"""Bounded serving warmup for prefill sizes and concurrent speculative rounds.

This sends real requests; run only within a guarded qualification/startup window.
Completion is not proof that every graph was measured. Retained counters and a
separate native trace establish coverage before adopting this startup treatment.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import threading
import time
import urllib.request

from flare_bench import digest, prompt_ids, stream, vocabulary

MODEL = 'nvidia/GLM-5.3-Flash-FP4-Local'
STAGES = ((1, 32768, 8), (2, 1024, 256), (4, 1024, 512))


def counters(text):
    result = {}
    for name in ('executions_total', 'execution_nanoseconds_total'):
        for reason in ('ordinary', 'discovery', 'timing_refresh', 'acceptance_learning'):
            key = f'flare_scheduler_{name}{{reason="{reason}"}}'
            values = [line.split()[1] for line in text.splitlines() if line.startswith(key + ' ')]
            if len(values) != 1 or not values[0].isdigit():
                raise ValueError(f'missing or invalid scheduler counter: {key}')
            result[key] = int(values[0])
    return result


def delta(before, after):
    if before.keys() != after.keys() or any(after[k] < v for k, v in before.items()):
        raise ValueError('scheduler counters reset during warmup')
    return {k: after[k] - v for k, v in before.items()}


def requests(vocab, identity, repetition, stage):
    concurrency, length, outputs = STAGES[stage]
    return [{'model': MODEL, 'prompt': prompt_ids(vocab, length,
                ['flare-shape-warmup-v1', identity, repetition, stage, index]),
             'max_tokens': outputs, 'temperature': 1., 'top_p': .95,
             'seed': 531717 + index, 'ignore_eos': True, 'stream': True,
             'stream_options': {'include_usage': True}} for index in range(concurrency)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True)
    parser.add_argument('--tokenizer', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    base = args.base.rstrip('/')
    vocab = vocabulary(args.tokenizer)

    def metrics():
        with urllib.request.urlopen(base + '/metrics', timeout=10) as response:
            return counters(response.read().decode())

    with args.out.open('x') as output:
        def emit(row):
            output.write(json.dumps(row) + '\n'); output.flush()

        emit({'manifest': {'schema': 1, 'stages': STAGES, 'repetitions': 2,
            'run_id': args.run_id, 'model': MODEL,
            'tokenizer_sha256': hashlib.sha256(args.tokenizer.read_bytes()).hexdigest(),
            'scope': 'startup workload; graph coverage and speed qualification separate'}})
        for repetition in range(2):
            for stage, (concurrency, length, budget) in enumerate(STAGES):
                bodies = requests(vocab, args.run_id, repetition, stage)
                barrier = threading.Barrier(concurrency)

                def run(body):
                    barrier.wait(timeout=30)
                    row = stream(base, '/v1/completions', body)
                    if (row['prompt_tokens'] != length or row['cached_tokens'] != 0
                            or row['completion_tokens'] != budget):
                        raise ValueError('warmup request length, output or cold-cache contract failed')
                    return {'request_sha256': digest(body), **row}

                before = metrics(); started = time.monotonic()
                with ThreadPoolExecutor(max_workers=concurrency) as pool:
                    rows = list(pool.map(run, bodies))
                changes = delta(before, metrics())
                emit({'repetition': repetition, 'stage': stage, 'requests': rows,
                      'wall_s': time.monotonic() - started, 'scheduler_delta': changes})
                print(json.dumps({'repetition': repetition, 'stage': stage,
                                  'requests': len(rows), 'scheduler_delta': changes}), flush=True)
        emit({'complete': True, 'requests': 14, 'repetitions': 2})


if __name__ == '__main__':
    main()
