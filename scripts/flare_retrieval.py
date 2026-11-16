"""Matched cold/forked retrieval client; stores hashes and verdicts, never raw text."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
from pathlib import Path
import threading
import time
import urllib.error
import urllib.request

from spec_metrics import counter_delta, parse_counters

FIXTURE_SHA256 = '5a25550356fe1490e0a28bbfa755efe2bec822695b21922a6ed533d2e5aa4098'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def load_fixture(source):
    if hashlib.sha256(source.read_bytes()).hexdigest() != FIXTURE_SHA256:
        raise ValueError('retrieval fixture differs from the pinned source')
    spec = importlib.util.spec_from_file_location('pinned_glm_retrieval', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def requests(fixture, mode, size, nonce, seed, concurrency, model):
    rows = []
    for index in range(concurrency):
        identity = f'{nonce}-{index}' if mode == 'cold' else nonce
        body, code, record = fixture.fixture(size, identity, seed + index, 1024, model)
        if mode == 'fork':
            body['messages'][0]['content'] += f'\nBranch {index}: give only the requested answer.'
        rows.append((body, code, record))
    return rows


def send(base, body):
    request = urllib.request.Request(base + '/v1/chat/completions', json.dumps(body).encode(),
                                     {'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            return json.load(response)
    except (OSError, ValueError) as error:
        return {'error': type(error).__name__}


def summarize(fixture, item, response, elapsed, mode):
    body, code, record = item
    try:
        verdict, _ = fixture.classify(response, code, record)
    except (KeyError, TypeError, IndexError):
        verdict = 'error'
    usage = response.get('usage') or {}
    cached = (usage.get('prompt_tokens_details') or {}).get('cached_tokens')
    cache_ok = type(cached) is int and (cached == 0 if mode == 'cold' else cached > 0)
    return {'request_sha256': digest(body), 'response_sha256': digest(response),
            'verdict': verdict, 'cache_observation_passed': cache_ok,
            'prompt_tokens': usage.get('prompt_tokens'), 'cached_tokens': cached,
            'completion_tokens': usage.get('completion_tokens'), 'elapsed_s': elapsed}


def graph_delta(before, after):
    if before is None or after is None:
        raise ValueError('missing speculative graph-shape counters')
    delta = {key: after.get(key, 0) - before.get(key, 0) for key in before.keys() | after.keys()}
    if any(n < 0 for n in delta.values()) or sum(delta.values()) <= 0:
        raise ValueError('graph-shape counters reset or did not advance')
    return {f'{b}x{w}': n for (b, w), n in delta.items() if n}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True)
    parser.add_argument('--engine', choices=('flare', 'vllm'), required=True)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--run-id', required=True, help='Use the same identity on both engines for matched requests')
    parser.add_argument('--model', default='nvidia/GLM-5.3-Flash-FP4-Local')
    parser.add_argument('--sizes', default='8000,60000', help='Fixture sizes, not exact token lengths')
    parser.add_argument('--concurrency', default='4,8')
    parser.add_argument('--reps', type=int, default=3)
    parser.add_argument('--modes', default='cold,fork')
    args = parser.parse_args()
    sizes, concurrencies = [int(n) for n in args.sizes.split(',')], [int(n) for n in args.concurrency.split(',')]
    modes = args.modes.split(',')
    if args.reps < 1 or min(sizes) < 120 or min(concurrencies) < 1 or set(modes) - {'cold', 'fork'}:
        parser.error('positive repetitions/concurrencies, fixture size >=120 and cold/fork modes required')
    fixture = load_fixture(args.fixture)
    base = args.base.rstrip('/')

    def counters():
        with urllib.request.urlopen(base + '/metrics', timeout=10) as response:
            return parse_counters(response.read().decode(), args.engine)

    failed = False
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x') as output:
        def emit(row):
            output.write(json.dumps(row) + '\n')
            output.flush()
            print(json.dumps(row), flush=True)

        emit({'manifest': {'fixture_sha256': FIXTURE_SHA256, 'engine': args.engine,
              'run_id': args.run_id, 'sizes': sizes, 'concurrencies': concurrencies,
              'modes': modes, 'reps': args.reps, 'temperature': 1, 'top_p': .95,
              'slot_cap': 4, 'qualification': 'retrieval/cache observations; not state-byte equivalence'}})
        for mode in modes:
            for size in sizes:
                for concurrency in concurrencies:
                    for rep in range(args.reps):
                        nonce = f'{args.run_id}-{mode}-{size}-{concurrency}-{rep}'
                        items = requests(fixture, mode, size, nonce, 1101 + rep * 100, concurrency, args.model)
                        if mode == 'fork':
                            warm = fixture.fixture(size, nonce, 1101 + rep * 100, 1, args.model)[0]
                            response = send(base, warm)
                            if 'error' in response or (response.get('usage') or {}).get('completion_tokens') != 1:
                                raise ValueError('fork-prefix warmup failed')
                        before = counters()
                        shapes_before = fixture.rounds(base) if args.engine == 'flare' else None
                        barrier = threading.Barrier(concurrency)

                        def run(item):
                            barrier.wait(timeout=30)
                            start = time.monotonic()
                            response = send(base, item[0])
                            return summarize(fixture, item, response, time.monotonic() - start, mode)

                        with ThreadPoolExecutor(concurrency) as pool:
                            rows = list(pool.map(run, items))
                        delta, shapes, metric_error = None, {}, None
                        try:
                            delta = counter_delta(before, counters(), args.engine)
                            if args.engine == 'flare':
                                shapes = graph_delta(shapes_before, fixture.rounds(base))
                        except (OSError, ValueError) as error:
                            metric_error = str(error)
                        bad = any(r['verdict'] in ('corrupt', 'error') or not r['cache_observation_passed'] for r in rows)
                        bad |= metric_error is not None
                        failed |= bad
                        emit({'mode': mode, 'size': size, 'concurrency': concurrency, 'rep': rep,
                              'requests': rows, 'counts': dict(Counter(r['verdict'] for r in rows)),
                              'speculative_delta': delta, 'round_shapes': shapes,
                              'metric_error': metric_error, 'hard_failure': bad})
                        if bad:
                            return 1
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
