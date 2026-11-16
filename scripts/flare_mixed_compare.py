"""Validate complete mixed-workload receipts and apply the registered descriptive gates.

Retains every repetition; does not infer statistical confidence or authorize adoption.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics

from flare_mixed_bench import validate_overlap

CASES = {
    'unequal_burst': {str(i): (n, 1, 0) for i, n in enumerate((131072, 32768, 8192, 4096))},
    'short_arrivals': {'long': (131072, 1, 0),
                       **{f'short{i}': (1024, 1, 2+2*i) for i in range(16)}},
    'decode_overlap': {'decode0': (None, 512, 0), 'decode1': (None, 512, 0),
                       'long': (32768, 1, None), 'short': (4096, 1, None)},
}


def finite(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def near(actual, expected):
    if not finite(actual) or not math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-9):
        raise ValueError('derived metric differs from retained timings')


def load(path, policy):
    records = [json.loads(line) for line in path.read_text().splitlines()]
    manifest = records[0]['manifest']
    for name, expected in {'schema': 1, 'policy': policy, 'reps': 3, 'slot_cap': 4,
                           'temperature': 1, 'top_p': .95}.items():
        if manifest.get(name) != expected:
            raise ValueError('mixed manifest differs from the registered workload')
    if records[-1] != {'complete': True, 'cases': 9, 'requests': 75}:
        raise ValueError('missing mixed completion footer')
    expected_keys = {(rep, case, name) for rep in range(3)
                     for case, items in CASES.items() for name in items}
    rows, cases, hashes = {}, {}, set()
    for row in records[1:-1]:
        case_key = row.get('rep'), row.get('case')
        if case_key not in {(rep, case) for rep in range(3) for case in CASES}:
            raise ValueError('unexpected mixed case')
        if row.get('event') == 'case_complete':
            if case_key in cases:
                raise ValueError('duplicate mixed case')
            cases[case_key] = row
            continue
        key = *case_key, row.get('id')
        if row.get('event') != 'request' or key not in expected_keys or key in rows:
            raise ValueError('failed, unexpected or duplicate mixed request')
        rows[key] = row
        length, budget, offset = CASES[key[1]][key[2]]
        if (type(row.get('prompt_tokens')) is not int or row['prompt_tokens'] <= 0 or
                (length is not None and row['prompt_tokens'] != length) or
                type(row['completion_tokens']) is not int or row['completion_tokens'] != budget or
                type(row['cached_tokens']) is not int or
                row['cached_tokens'] != 0 or row['scheduled_offset_s'] != offset):
            raise ValueError('mixed request differs from the cold exact-token fixture')
        for name in ('input_sha256', 'output_sha256'):
            value = row[name]
            if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
                raise ValueError('invalid mixed request digest')
        if row['input_sha256'] in hashes:
            raise ValueError('repeated mixed request identity')
        hashes.add(row['input_sha256'])
        start, end, deliveries = row['start_s'], row['end_s'], row['delivery_times_s']
        if (not deliveries or any(not finite(x) for x in (start, end, *deliveries)) or
                not start < deliveries[0] <= deliveries[-1] <= end or
                any(b < a for a, b in zip(deliveries, deliveries[1:]))):
            raise ValueError('invalid mixed delivery timing')
        if offset is not None and abs(start-offset) > .25:
            raise ValueError('mixed arrival missed its registered offset')
        near(row['ttft_s'], deliveries[0]-start)
        near(row['elapsed_s'], end-start)
        gaps = sorted(b-a for a, b in zip(deliveries, deliveries[1:]))
        if gaps:
            near(row['delivery_gap_p95_s'], gaps[math.ceil(.95*len(gaps))-1])
            near(row['delivery_gap_max_s'], gaps[-1])
        elif row['delivery_gap_p95_s'] is not None or row['delivery_gap_max_s'] is not None:
            raise ValueError('invented within-burst delivery gaps')
    if rows.keys() != expected_keys or len(cases) != 9:
        raise ValueError('incomplete mixed request or case coverage')
    for (rep, case), result in cases.items():
        cohort = [rows[rep, case, name] for name in CASES[case]]
        if (result['request_count'] != len(cohort) or not finite(result['wall_s']) or
                result['wall_s'] < max(r['end_s'] for r in cohort)):
            raise ValueError('inconsistent mixed case completion')
        if case == 'decode_overlap' and result['overlap'] != validate_overlap(cohort):
            raise ValueError('mixed overlap evidence differs')
    return manifest, rows, cases


def distribution(reference, candidate, higher_better=False):
    change = statistics.median(candidate)/statistics.median(reference)-1
    separated = (max(candidate) < .98*min(reference) if higher_better
                 else min(candidate) > 1.02*max(reference))
    median_bad = change < -.02 if higher_better else change > .02
    return {'reference_reps': reference, 'candidate_reps': candidate,
            'median_change_pct': 100*change,
            'observation': ('separated_regression_over_2pct' if separated else
                            'median_regression_repeat_needed' if median_bad else
                            'no_median_regression_over_2pct_observed')}


def compare(reference, candidate):
    bm, br, bc = reference
    cm, cr, cc = candidate
    if {k: v for k, v in bm.items() if k != 'policy'} != {k: v for k, v in cm.items() if k != 'policy'}:
        raise ValueError('mixed arm manifests differ')
    groups = defaultdict(lambda: [[], []])
    for key in sorted(br):
        b, c = br[key], cr[key]
        if b['input_sha256'] != c['input_sha256'] or b['prompt_tokens'] != c['prompt_tokens']:
            raise ValueError('mixed request bodies differ between arms')
        for arm, row in enumerate((b, c)):
            values = {k: row[k] for k in ('ttft_s', 'elapsed_s')}
            if key[2].startswith('decode'):
                values.update({k: row[k] for k in ('delivery_gap_p95_s', 'delivery_gap_max_s')})
                # End-to-end completion rate; includes TTFT and all output tokens.
                values['completion_tok_s'] = row['completion_tokens']/row['elapsed_s']
                span = row['elapsed_s'] - row['ttft_s']
                if span <= 0:
                    raise ValueError('missing post-first-output decode interval')
                values['amortized_decode_tok_s'] = (row['completion_tokens']-1)/span
            for metric, value in values.items():
                if value is None or value <= 0:
                    raise ValueError('missing positive mixed comparison metric')
                groups[key[1], key[2], metric][arm].append(value)
    for rep, case in sorted(bc):
        for arm, data in enumerate((bc, cc)):
            groups[case, 'cohort', 'wall_s'][arm].append(data[rep, case]['wall_s'])
    return [{'case': case, 'request': name, 'metric': metric,
             **distribution(*values, higher_better=metric.endswith('_tok_s'))}
            for (case, name, metric), values in sorted(groups.items())]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', required=True, type=Path)
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    result = {'schema': 1, 'requests_per_arm': 75, 'cases_per_arm': 9,
              'reference_sha256': hashlib.sha256(args.reference.read_bytes()).hexdigest(),
              'candidate_sha256': hashlib.sha256(args.candidate.read_bytes()).hexdigest(),
              'method': 'Matched request identities, three repetitions per request role. '
                        'Delivery gaps are streamed-output gaps, not inferred per-token times. '
                        'Separated 2% gate is descriptive, not a confidence interval or adoption decision.',
              'points': compare(load(args.reference, 'balanced'), load(args.candidate, 'latency'))}
    with args.out.open('x') as output:
        json.dump(result, output, indent=2, allow_nan=False)
        output.write('\n')
    print('Validated 75 requests and 9 cases per arm')


if __name__ == '__main__':
    main()
