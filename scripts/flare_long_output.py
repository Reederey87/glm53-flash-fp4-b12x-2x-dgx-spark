"""Matched long-prompt/256-output workload; retains timings, not generated text."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
from pathlib import Path
import threading
import time
import urllib.request

from flare_bench import prompt_ids, vocabulary, stream
from flare_mixed_bench import observe, summarize
from flare_mixed_compare import distribution
from spec_metrics import counter_delta, parse_counters

LENGTHS = (131072, 32768, 8192, 4096)
BUDGET = 256


def bodies(vocab, run_id, rep):
    return [{'model': 'nvidia/GLM-5.3-Flash-FP4-Local', 'temperature': 1,
             'top_p': .95, 'ignore_eos': True, 'seed': 20261116 + rep, 'stream': True,
             'stream_options': {'include_usage': True}, 'max_tokens': BUDGET,
             'prompt': prompt_ids(vocab, length, [run_id, 'long-output', rep, i])}
            for i, length in enumerate(LENGTHS)]


def load(path):
    records = [json.loads(line) for line in path.read_text().splitlines()]
    manifest = records[0]['manifest']
    if (manifest.get('schema') != 2 or manifest.get('ignore_eos') is not True or manifest.get('reps') != 3 or
            manifest.get('lengths') != list(LENGTHS) or manifest.get('output_budget') != BUDGET or
            manifest.get('temperature') != 1 or manifest.get('top_p') != .95 or
            manifest.get('slot_cap') != 4 or manifest.get('policy') not in ('balanced', 'latency')):
        raise ValueError('unexpected long-output manifest')
    if len(records) != 5 or records[-1] != {'complete': True, 'requests': 12}:
        raise ValueError('incomplete long-output receipt')
    seen = set()
    for rep, batch in enumerate(records[1:-1]):
        if batch['rep'] != rep or len(batch['requests']) != 4:
            raise ValueError('missing or duplicate long-output batch')
        if type(batch['wall_s']) not in (int, float) or not math.isfinite(batch['wall_s']) or batch['wall_s'] <= 0:
            raise ValueError('invalid long-output wall time')
        for length, row in zip(LENGTHS, batch['requests'], strict=True):
            if row['prompt_tokens'] != length:
                raise ValueError('long-output prompt count changed')
            checked = summarize({'max_tokens': BUDGET}, row['start_s'], row['end_s'],
                row['delivery_times_s'], {'prompt_tokens': length,
                    'completion_tokens': row['completion_tokens'],
                    'prompt_tokens_details': {'cached_tokens': row['cached_tokens']}},
                True, row['output_sha256'])
            for key in ('ttft_s', 'elapsed_s', 'delivery_gap_p95_s', 'delivery_gap_max_s'):
                if row[key] != checked[key] or row[key] is None or row[key] <= 0:
                    raise ValueError('invalid long-output timing')
            if row['end_s'] > batch['wall_s'] or row['start_s'] > .25:
                raise ValueError('long-output barrier or wall timing failed')
            for key in ('input_sha256', 'output_sha256'):
                value = row[key]
                if len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
                    raise ValueError('invalid long-output digest')
            if row['input_sha256'] in seen:
                raise ValueError('duplicate long-output request')
            seen.add(row['input_sha256'])
        # Revalidate raw counter snapshots instead of trusting derived rates.
        delta = counter_delta(batch['counters_before'], batch['counters_after'], 'flare')
        if delta != batch['speculative_delta']:
            raise ValueError('long-output speculative delta changed')
    return manifest, records[1:-1]


def compare(reference, candidate):
    bm, br = load(reference)
    cm, cr = load(candidate)
    if bm['policy'] != 'balanced' or cm['policy'] != 'latency':
        raise ValueError('expected balanced reference and latency candidate')
    if {k: v for k, v in bm.items() if k != 'policy'} != {k: v for k, v in cm.items() if k != 'policy'}:
        raise ValueError('long-output manifests differ')
    for b, c in zip(br, cr, strict=True):
        if [r['input_sha256'] for r in b['requests']] != [r['input_sha256'] for r in c['requests']]:
            raise ValueError('long-output request bodies differ')
    points = []
    for i, length in enumerate(LENGTHS):
        for metric in ('ttft_s', 'elapsed_s', 'delivery_gap_p95_s', 'delivery_gap_max_s'):
            points.append({'length': length, 'metric': metric,
                **distribution([r['requests'][i][metric] for r in br],
                               [r['requests'][i][metric] for r in cr], higher_better=False)})
    points.append({'metric': 'cohort_wall_s', **distribution(
        [b['wall_s'] for b in br], [b['wall_s'] for b in cr], higher_better=False)})
    return {'requests_per_arm': 12, 'points': points,
            'limitations': ['Output delivery gaps are not individual-token gaps.',
                'This is scheduler stress, not semantic accuracy or full-model numerical equivalence.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    run = sub.add_parser('run')
    run.add_argument('--base', required=True)
    run.add_argument('--policy', choices=('balanced', 'latency'), required=True)
    run.add_argument('--tokenizer', type=Path, required=True)
    run.add_argument('--run-id', required=True)
    report = sub.add_parser('compare')
    report.add_argument('--reference', type=Path, required=True)
    report.add_argument('--candidate', type=Path, required=True)
    for command in (run, report):
        command.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'compare':
        result = compare(args.reference, args.candidate)
        with args.out.open('x') as out:
            json.dump(result, out, indent=2, allow_nan=False)
            out.write('\n')
        return
    vocab = vocabulary(args.tokenizer)
    base = args.base.rstrip('/')
    with args.out.open('x') as out, args.out.with_suffix('.requests.jsonl').open('x') as raw_out:
        raw_lock = threading.Lock()
        def journal(rep, index, row):
            with raw_lock:
                raw_out.write(json.dumps({'rep': rep, 'request_index': index, **row}, allow_nan=False)+'\n')
                raw_out.flush()
        def emit(row):
            out.write(json.dumps(row, allow_nan=False) + '\n')
            out.flush()
        emit({'manifest': {'schema': 2, 'ignore_eos': True, 'policy': args.policy, 'run_id': args.run_id,
            'tokenizer_sha256': hashlib.sha256(args.tokenizer.read_bytes()).hexdigest(),
            'reps': 3, 'lengths': LENGTHS, 'output_budget': BUDGET,
            'temperature': 1, 'top_p': .95, 'slot_cap': 4}})
        warm = bodies(vocab, args.run_id, -1)[0]
        warm.update(prompt=warm['prompt'][:128], max_tokens=8)
        stream(base, '/v1/completions', warm)
        def counters():
            with urllib.request.urlopen(base + '/metrics', timeout=10) as response:
                return parse_counters(response.read().decode(), 'flare')
        for rep in range(3):
            items = bodies(vocab, args.run_id, rep)
            barrier = threading.Barrier(4)
            before = counters()
            epoch = time.monotonic()
            def worker(item):
                index, body = item
                barrier.wait(timeout=10)
                return observe(base, '/v1/completions', body, epoch,
                               journal=lambda row: journal(rep, index, row))
            with ThreadPoolExecutor(4) as pool:
                rows = list(pool.map(worker, enumerate(items)))
            wall = time.monotonic() - epoch
            after = counters()
            emit({'rep': rep, 'requests': rows, 'wall_s': wall,
                  'counters_before': before, 'counters_after': after,
                  'speculative_delta': counter_delta(before, after, 'flare')})
            print(f'long-output rep{rep}: four cold prompts,256 outputs each', flush=True)
        emit({'complete': True, 'requests': 12})
    load(args.out)


if __name__ == '__main__':
    main()
