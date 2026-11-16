"""Validate fixed ABBA repeats without treating requests as independent starts."""
import argparse
import hashlib
import json
from pathlib import Path

import flare_long_output as long_output
import flare_mixed_compare as mixed

ORDER = ('balanced', 'latency', 'latency', 'balanced')


def higher_better(metric):
    return metric.endswith('_tok_s') or metric in ('mean_acceptance_length', 'draft_acceptance_rate')


def key(workload, row):
    return (workload, row.get('case'), row.get('request'), row.get('length'), row['metric'])


def report(directory):
    invocations = {'head': set(), 'worker': set()}
    provenance = {}
    for i, policy in enumerate(ORDER):
        for node in invocations:
            prefix = directory / f'{i}-{policy}-{node}'
            identity = json.loads(prefix.with_name(prefix.name + '-identity.json').read_text())
            terminal = json.loads(prefix.with_name(prefix.name + '-exit.json').read_text())
            invocation = prefix.with_name(prefix.name + '-invocation.txt').read_text().strip()
            assert invocation and invocation not in invocations[node], 'ABBA requires distinct native invocations'
            invocations[node].add(invocation)
            assert terminal['invocation_id'] == invocation and terminal['native_returncode'] == 0
            assert terminal['forced_kill'] is False
            assert identity['policy'] == policy and identity['trace'] is False
            frozen = {k: v for k, v in identity.items() if k not in ('time', 'pid', 'policy')}
            if node in provenance:
                assert frozen == provenance[node], 'ABBA serving controls changed'
            provenance[node] = frozen
    files = {(i, workload): directory / f'{i}-{policy}-{workload}.jsonl'
             for i, policy in enumerate(ORDER) for workload in ('mixed', 'long-output')}
    loaded = {i: mixed.load(files[i, 'mixed'], policy) for i, policy in enumerate(ORDER)}
    longs = {i: long_output.load(files[i, 'long-output']) for i in range(4)}
    for i in range(1, 4):
        for group in (loaded, longs):
            assert {k: v for k, v in group[0][0].items() if k != 'policy'} == {
                k: v for k, v in group[i][0].items() if k != 'policy'}, 'ABBA manifests differ'
        assert {k: v['input_sha256'] for k, v in loaded[0][1].items()} == {
            k: v['input_sha256'] for k, v in loaded[i][1].items()}, 'ABBA mixed bodies differ'
        assert [[r['input_sha256'] for r in b['requests']] for b in longs[0][1]] == [
            [r['input_sha256'] for r in b['requests']] for b in longs[i][1]], 'ABBA long bodies differ'
    pairs = []
    for reference, candidate in ((0, 1), (3, 2)):
        rows = [('mixed', r) for r in mixed.compare(loaded[reference], loaded[candidate])]
        rows += [('long-output', r) for r in long_output.compare(
            files[reference, 'long-output'], files[candidate, 'long-output'])['points']]
        for metric in ('mean_acceptance_length', 'draft_acceptance_rate'):
            values = []
            for arm in (reference, candidate):
                rates = []
                for batch in longs[arm][1]:
                    delta = batch['speculative_delta']
                    assert delta['drafts'] > 0 and delta['draft_tokens'] > 0
                    rates.append(1 + delta['accepted'] / delta['drafts'] if metric == 'mean_acceptance_length'
                                 else delta['accepted'] / delta['draft_tokens'])
                values.append(rates)
            rows.append(('long-output', {'metric': metric, **mixed.distribution(*values, higher_better=True)}))
        points = {key(workload, r): {'workload': workload, **r} for workload, r in rows}
        assert len(points) == 80
        pairs.append(points)
    assert pairs[0].keys() == pairs[1].keys()
    combined = []
    for point, first in pairs[0].items():
        second = pairs[1][point]
        reference = first['reference_reps'] + second['reference_reps']
        candidate = first['candidate_reps'] + second['candidate_reps']
        assert len(reference) == len(candidate) == 6
        values = mixed.distribution(reference, candidate, higher_better=higher_better(first['metric']))
        identity = {k: first[k] for k in ('workload', 'case', 'request', 'length', 'metric') if k in first}
        combined.append({**identity, **values, 'forward_pair': first, 'reverse_pair': second})
    unresolved = [r for r in combined if r['observation'] != 'no_median_regression_over_2pct_observed'
                  or any(r[p]['observation'] == 'separated_regression_over_2pct'
                         for p in ('forward_pair', 'reverse_pair'))]
    return {'schema': 1, 'order': ORDER, 'fresh_starts_per_policy': 2,
            'measured_repetitions_per_policy': 6, 'requests_per_policy': 174,
            'points': combined, 'requires_investigation': unresolved,
            'repeat_gate_passed': not unresolved,
            'native_invocations': {k: sorted(v) for k, v in invocations.items()},
            'frozen_native_identity': provenance,
            'receipt_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files.values()},
            'limitations': ['One counterbalanced block; six requests per role are not six independent starts.',
                            'Descriptive 2% gate, not a confidence interval or production-adoption decision.',
                            'All earlier failed and overlapping measurements remain retained.',
                            'Full speed/acceptance, numerical, context, capacity and recovery gates remain.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = report(args.directory)
    with args.out.open('x') as out:
        json.dump(result, out, indent=2, allow_nan=False)
        out.write('\n')
    print(json.dumps({'points': len(result['points']),
                      'requires_investigation': len(result['requires_investigation']),
                      'repeat_gate_passed': result['repeat_gate_passed']}))


if __name__ == '__main__':
    main()
