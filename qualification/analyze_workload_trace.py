"""Validate complete native histories for the retained ABBA workloads.

This is a diagnostic, never an untraced performance verdict. Native generations
are not asserted to be HTTP request IDs; graph gaps are not token-delivery gaps.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import flare_long_output
import flare_mixed_compare
from flare_trace_check import integer


def analyze(rows, expected_lengths):
    header, end = rows[0], rows[-1]
    assert header['event'] == 'manifest' and header['schema'] == 1
    assert end['event'] == 'complete' and end['complete'] is True
    assert end['reason'] == 'stopped' and end['truncated'] is False
    assert end['dropped_updates'] == 0
    graphs = {g['graph']: g for g in header['graphs']}
    assert len(graphs) == len(header['graphs'])
    histories, events = defaultdict(list), defaultdict(list)
    completions = []
    previous = header['started_at_ns']
    for row in rows[1:-1]:
        if row['event'] == 'state':
            continue
        assert row['event'] == 'completion' and row['graph'] in graphs
        assert row['fence'] == len(completions) + 1
        assert all(integer(row[k]) for k in ('at_ns', 'selected_at_ns', 'commit_ns', 'wall_ns'))
        assert previous <= row['at_ns'] and row['selected_at_ns'] <= row['commit_ns'] <= row['at_ns']
        assert row['gpu_ns'] is None or integer(row['gpu_ns'], 1)
        previous = row['at_ns']
        kind = graphs[row['graph']]['kind']
        seen = set()
        for lane in row['lanes']:
            assert integer(lane['slot']) and lane['slot'] < 64 and lane['slot'] not in seen
            assert integer(lane['generation'], 1)
            assert integer(lane['start_position']) and integer(lane['tokens'])
            seen.add(lane['slot'])
            key = lane['slot'], lane['generation']
            item = {'fence': row['fence'], 'graph': graphs[row['graph']]['name'],
                    'kind': kind, 'at_ns': row['at_ns'], 'selected_at_ns': row['selected_at_ns'],
                    'gpu_ns': row['gpu_ns'], 'wall_ns': row['wall_ns'],
                    'timing_origin': row['timing_origin'], 'estimate_ns': row['estimate_ns'], **lane}
            events[key].append(item)
            if kind == 'Prefill':
                assert lane['tokens'] > 0
                histories[key].append(item)
        completions.append(row)
    assert end['completions'] == len(completions) and end['at_ns'] >= previous
    result = []
    for key, prefill in histories.items():
        position = 0
        for row in prefill:
            assert row['start_position'] == position
            position += row['tokens']
        decode = [r for r in events[key] if r['kind'] in ('Decode', 'Speculative')]
        gaps = [{'gap_ns': b['at_ns'] - a['at_ns'], 'from_fence': a['fence'], 'to_fence': b['fence']}
                for a, b in zip(decode, decode[1:])]
        result.append({'native_request': key, 'prompt_tokens': position,
                       'first_prefill_selected_ns': prefill[0]['selected_at_ns'],
                       'prefill_finished_ns': prefill[-1]['at_ns'],
                       'largest_decode_completion_gaps': sorted(gaps, key=lambda r: r['gap_ns'], reverse=True)[:5],
                       'events': events[key]})
    assert Counter(r['prompt_tokens'] for r in result) == Counter(expected_lengths)
    return {'native_histories': len(result), 'completions': len(completions),
            'prompt_tokens': sum(expected_lengths), 'histories': result,
            'scope': 'Complete native graph histories; no HTTP identity mapping or performance verdict.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('label')
    parser.add_argument('policy', choices=('balanced', 'latency'))
    parser.add_argument('workload', choices=('mixed', 'long-output'))
    args = parser.parse_args()
    source = args.directory / f'{args.label}-{args.workload}.jsonl'
    if args.workload == 'mixed':
        _, requests, _ = flare_mixed_compare.load(source, args.policy)
        lengths = [r['prompt_tokens'] for r in requests.values()]
    else:
        _, batches = flare_long_output.load(source)
        lengths = [r['prompt_tokens'] for b in batches for r in b['requests']]
    result = analyze([json.loads(x) for x in (args.directory / f'{args.label}-trace.jsonl').read_text().splitlines()],
                     [128, *lengths])
    with (args.directory / f'{args.label}-analysis.json').open('x') as out:
        json.dump(result, out, indent=2)
        out.write('\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'histories'}), flush=True)


if __name__ == '__main__':
    main()
