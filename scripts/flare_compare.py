"""Validate and compare complete matched Flare/B12X benchmark receipts.

Never makes an adoption decision. All repetition values remain in the report.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics

LENGTHS = (8192, 16384, 32768, 65536, 131072)
CONCURRENCIES = (1, 2, 4, 8)


def positive(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def near(actual, expected):
    if not positive(actual) or not math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-9):
        raise ValueError('derived metric disagrees with its source measurements')


def key(row):
    return row['kind'], row['rep'], row['concurrency'], row.get('length', row.get('task'))


def load(path, engine):
    records = [json.loads(line) for line in path.read_text().splitlines()]
    manifest = records[0]['manifest']
    if manifest['engine'] != engine or manifest['schema'] != 1:
        raise ValueError('unexpected receipt engine or schema')
    if (manifest['reps'] not in (3, 5) or manifest['decode_budget'] != 200 or
            manifest['slot_cap'] != 4 or manifest['temperature'] != 1 or manifest['top_p'] != .95):
        raise ValueError('receipt differs from the registered matrix')
    expected = {(kind, rep, c, point)
                for rep in range(manifest['reps']) for c in CONCURRENCIES
                for kind, points in (('prefill', LENGTHS), ('decode', ('prose', 'code')))
                for point in points}
    rows = {}
    request_hashes = set()
    for row in records[1:]:
        identity = key(row)
        if identity not in expected or identity in rows:
            raise ValueError('unexpected or duplicate matrix row')
        rows[identity] = row
        if row['slot_cap'] != 4 or len(row['requests']) != row['concurrency'] or not positive(row['wall_s']):
            raise ValueError('missing request or invalid batch measurement')
        for request in row['requests']:
            for name in ('input_sha256', 'output_sha256'):
                value = request[name]
                if len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
                    raise ValueError('invalid request/output digest')
            if request['input_sha256'] in request_hashes:
                raise ValueError('repeated request identity')
            request_hashes.add(request['input_sha256'])
            if any(not positive(request[name]) for name in ('ttft_s', 'elapsed_s', 'decode_span_s')):
                raise ValueError('invalid request timing')
            near(request['elapsed_s'], request['ttft_s'] + request['decode_span_s'])
            wanted = 1 if row['kind'] == 'prefill' else manifest['decode_budget']
            if request['completion_tokens'] != wanted:
                raise ValueError('actual completion length differs from the registered budget')
            near(request['decode_tok_s'], wanted / request['decode_span_s'])
            if not isinstance(request['prompt_tokens'], int) or request['prompt_tokens'] <= 0:
                raise ValueError('invalid prompt count')
            if type(request['cached_tokens']) is not int or not 0 <= request['cached_tokens'] <= request['prompt_tokens']:
                raise ValueError('invalid cache observation')
            if row['kind'] == 'prefill':
                if request['prompt_tokens'] != row['length'] or request['cached_tokens'] != 0:
                    raise ValueError('prefill is not exact-length and cold')
                near(request['prefill_tok_s'], row['length'] / request['ttft_s'])
        if row['kind'] == 'decode':
            delta = row['speculative_delta']
            if any(not positive(delta[name]) for name in ('drafts', 'draft_tokens')):
                raise ValueError('speculative counters did not advance')
            if not math.isfinite(delta['accepted']) or not 0 <= delta['accepted'] <= delta['draft_tokens']:
                raise ValueError('invalid accepted draft count')
            if engine == 'flare' and (not positive(delta['rounds']) or delta['rounds'] < delta['drafts']):
                raise ValueError('invalid native verification round evidence')
            near(row['aggregate_tok_s'], sum(r['completion_tokens'] for r in row['requests']) / row['wall_s'])
            near(row['acceptance_length'], 1 + delta['accepted'] / delta['drafts'])
            if not math.isclose(row['draft_accept_rate'], delta['accepted'] / delta['draft_tokens'], rel_tol=1e-9):
                raise ValueError('draft acceptance metric disagrees with its counters')
    if rows.keys() != expected:
        raise ValueError('incomplete benchmark matrix')
    return manifest, rows


def distributions(reference, candidate):
    baseline, treatment = statistics.median(reference), statistics.median(candidate)
    delta = 100 * (treatment / baseline - 1) if baseline else None
    if max(candidate) < .98 * min(reference):
        verdict = 'separated_regression_over_2pct'
    elif delta is not None and delta < -2:
        verdict = 'median_regression_repeat_needed'
    else:
        verdict = 'no_median_regression_over_2pct_observed'
    return {'reference_reps': reference, 'candidate_reps': candidate,
            'reference_median': baseline, 'candidate_median': treatment,
            'median_change_pct': delta, 'observation': verdict}


def compare(reference, candidate):
    bm, br = reference
    cm, cr = candidate
    if {k: v for k, v in bm.items() if k != 'engine'} != {k: v for k, v in cm.items() if k != 'engine'}:
        raise ValueError('benchmark manifests differ')
    groups = defaultdict(lambda: defaultdict(lambda: [[], []]))
    for identity in sorted(br):
        b, c = br[identity], cr[identity]
        if [r['input_sha256'] for r in b['requests']] != [r['input_sha256'] for r in c['requests']]:
            raise ValueError('request bodies differ between engines')
        if [r['prompt_tokens'] for r in b['requests']] != [r['prompt_tokens'] for r in c['requests']]:
            raise ValueError('prompt token counts differ between engines')
        point = (identity[0], identity[2], identity[3])
        for arm, row in enumerate((b, c)):
            if row['kind'] == 'prefill':
                values = {'per_request_prefill_tok_s': statistics.median(r['prefill_tok_s'] for r in row['requests']),
                          'aggregate_prompt_tok_s': sum(r['prompt_tokens'] for r in row['requests']) / row['wall_s']}
            else:
                values = {name: row[name] for name in ('aggregate_tok_s', 'acceptance_length', 'draft_accept_rate')}
                values['per_request_decode_tok_s'] = statistics.median(r['decode_tok_s'] for r in row['requests'])
            for metric, value in values.items():
                groups[point][metric][arm].append(value)
    return [{'kind': kind, 'concurrency': concurrency, 'point': point, 'slot_cap': 4,
             'metrics': {name: distributions(*values) for name, values in metrics.items()}}
            for (kind, concurrency, point), metrics in sorted(groups.items())]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    baseline, candidate = load(args.reference, 'vllm'), load(args.candidate, 'flare')
    report = {'schema': 1, 'reference_sha256': hashlib.sha256(args.reference.read_bytes()).hexdigest(),
              'candidate_sha256': hashlib.sha256(args.candidate.read_bytes()).hexdigest(),
              'manifest': candidate[0], 'rows_per_arm': len(candidate[1]),
              'method': 'Median of repetitions; per-request metrics first use the within-batch median. '
                        'Separated regression means best candidate <98% of worst reference. '
                        'This is a conservative descriptive rule, not a confidence interval or adoption decision.',
              'limitations': ['TTFT includes queueing; concurrency eight exceeds the four active slots.',
                              'Decode rate includes the first streamed burst; it is not inverse standard TPOT.',
                              'Output distributions can differ across engines despite identical request seeds.',
                              'Quality, memory, capacity and lifecycle gates remain separate.'],
              'points': compare(baseline, candidate)}
    with args.out.open('x') as output:
        json.dump(report, output, indent=2, allow_nan=False)
        output.write('\n')
    print(f"Validated {report['rows_per_arm']} matched rows per arm; report: {args.out}")


if __name__ == '__main__':
    main()
