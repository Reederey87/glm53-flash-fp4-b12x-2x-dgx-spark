"""Validate native completion order and its matched four-prompt client receipts.

Completion observations identify native slot generations, not HTTP request IDs.
The report compares cohort order and sorted client TTFTs without inventing a
per-request mapping or treating traced timings as a clean performance result.
"""
import argparse
from collections import defaultdict
import hashlib
from itertools import groupby
import json
import math
from pathlib import Path


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def trace(records, length=131072, concurrency=4):
    if len(records) < 3 or records[0].get('event') != 'manifest' or records[0].get('schema') != 1:
        raise ValueError('missing trace manifest')
    end = records[-1]
    if (end.get('event') != 'complete' or end.get('complete') is not True or
            end.get('dropped_updates') != 0 or end.get('truncated') is not False or
            end.get('reason') not in ('stopped', 'duration')):
        raise ValueError('incomplete, dropped or truncated trace')
    catalog = records[0]['graphs']
    graphs = {g['graph']: g for g in catalog}
    if len(graphs) != len(catalog) or not all(integer(g) for g in graphs):
        raise ValueError('duplicate or invalid graph identities')
    histories = defaultdict(list)
    completions = []
    previous_fence, previous_at = -1, records[0]['started_at_ns']
    for row in records[1:-1]:
        if row.get('event') == 'state':
            continue
        if row.get('event') != 'completion' or row.get('graph') not in graphs:
            raise ValueError('unknown trace event or graph')
        if any(not integer(row.get(k)) for k in ('fence', 'at_ns', 'selected_at_ns', 'commit_ns', 'wall_ns')):
            raise ValueError('invalid native timing or fence')
        if not (previous_fence < row['fence'] and previous_at <= row['at_ns'] and
                row['selected_at_ns'] <= row['commit_ns'] <= row['at_ns']):
            raise ValueError('unordered native completion or selection times')
        previous_fence, previous_at = row['fence'], row['at_ns']
        if row['gpu_ns'] is not None and not integer(row['gpu_ns'], 1):
            raise ValueError('invalid observed GPU duration')
        seen = set()
        for lane in row['lanes']:
            if (not integer(lane.get('slot')) or lane['slot'] >= 64 or
                    not integer(lane.get('generation'), 1) or
                    not integer(lane.get('start_position')) or not integer(lane.get('tokens'))):
                raise ValueError('invalid native lane identity or extent')
            if lane['slot'] in seen:
                raise ValueError('duplicate slot within a completion')
            seen.add(lane['slot'])
            if graphs[row['graph']]['kind'] == 'Prefill':
                if not lane['tokens']:
                    raise ValueError('empty prefill extent')
                key = (lane['slot'], lane['generation'])
                histories[key].append({'fence': row['fence'], 'at_ns': row['at_ns'], **lane})
        completions.append(row)
    if (end.get('completions') != len(completions) or not integer(end.get('at_ns')) or
            end['at_ns'] < previous_at):
        raise ValueError('trace footer count or clock differs')
    targets = {key: rows for key, rows in histories.items()
               if max(r['start_position']+r['tokens'] for r in rows) >= length//2}
    if len(targets) != concurrency:
        raise ValueError('missing or extra long-prompt histories')
    for rows in targets.values():
        position = 0
        for row in rows:
            if row['start_position'] != position:
                raise ValueError('prefill history is missing, duplicated or overlapping')
            position += row['tokens']
        if position != length:
            raise ValueError('long-prompt work is incomplete or exceeds the fixture')
    order = sorted((row for rows in targets.values() for row in rows), key=lambda r: r['fence'])
    work, finishes, runs = 0, [], []
    for _, group in groupby(order, key=lambda r: r['fence']):
        cohort = list(group)
        keys = sorted([row['slot'], row['generation']] for row in cohort)
        tokens = sum(row['tokens'] for row in cohort)
        work += tokens
        if runs and runs[-1]['requests'] == keys:
            runs[-1]['tokens'] += tokens
            runs[-1]['completions'] += 1
        else:
            runs.append({'requests': keys, 'tokens': tokens, 'completions': 1})
        for row in cohort:
            if row['start_position'] + row['tokens'] == length:
                finishes.append({'request': [row['slot'], row['generation']],
                                 'at_ns': row['at_ns'], 'fence': row['fence'],
                                 'cohort_prompt_tokens_completed': work})
    return {'total_prompt_work': work, 'prefill_completions': len(order),
            'service_runs': runs, 'prompt_finishes': finishes,
            'scope': 'native graph completions; HTTP request-to-slot mapping is not observed'}


def probe(records):
    manifest = records[0]['manifest']
    if any(manifest.get(k) != v for k, v in {
            'schema': 1, 'engine': 'flare', 'seed': 20261115, 'reps': 1,
            'slot_cap': 4, 'decode_budget': 200, 'temperature': 1, 'top_p': .95}.items()):
        raise ValueError('probe differs from the registered workload')
    rows = [r for r in records[1:] if r.get('kind') == 'prefill']
    if len(rows) != 1 or rows[0]['length'] != 131072 or rows[0]['concurrency'] != 4 or rows[0]['rep'] != 0:
        raise ValueError('expected one four-prompt probe')
    requests = rows[0]['requests']
    if len(requests) != 4:
        raise ValueError('missing client request')
    for r in requests:
        if r['prompt_tokens'] != 131072 or r['completion_tokens'] != 1 or r['cached_tokens'] != 0:
            raise ValueError('probe was not exact, complete and cold')
        for k in ('ttft_s', 'elapsed_s'):
            if not isinstance(r[k], (int, float)) or not math.isfinite(r[k]) or r[k] <= 0:
                raise ValueError('invalid client timing')
        if r['ttft_s'] > r['elapsed_s']:
            raise ValueError('client first output after stream completion')
        h = r['input_sha256']
        if not isinstance(h, str) or len(h) != 64 or any(c not in '0123456789abcdef' for c in h):
            raise ValueError('invalid client request hash')
    hashes = sorted(r['input_sha256'] for r in requests)
    if len(set(hashes)) != 4:
        raise ValueError('repeated client fixture')
    return {'request_hashes': hashes, 'sorted_ttft_s': sorted(r['ttft_s'] for r in requests),
            'tokenizer_sha256': manifest['tokenizer_sha256']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace', type=Path, required=True)
    parser.add_argument('--probe', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = {}
    for name, path, check in (('native', args.trace, trace), ('client', args.probe, probe)):
        data = path.read_bytes()
        if name == 'native' and len(data) > 16 * 1024 * 1024:
            raise ValueError('trace exceeds the registered file bound')
        result[name] = check([json.loads(line) for line in data.splitlines()])
        result[name]['receipt_sha256'] = hashlib.sha256(data).hexdigest()
    with args.out.open('x') as output:
        json.dump(result, output, indent=2, allow_nan=False)
        output.write('\n')
    print(json.dumps({'validated': True, 'prompt_finishes': result['native']['prompt_finishes'],
                      'sorted_ttft_s': result['client']['sorted_ttft_s']}))


if __name__ == '__main__':
    main()
