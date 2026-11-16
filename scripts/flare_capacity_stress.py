"""Observe two concurrent exact-million-token prompts under an external guard.

This is admission/stream/capacity evidence, not a retrieval-quality benchmark.
The caller owns memory enforcement, runtime identity, exit checks and rollback.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
from pathlib import Path
import threading
import time
import urllib.request

from flare_bench import digest, prompt_ids, stream, vocabulary
from flare_production import validate_capacity
from spec_metrics import parse_counters, counter_delta


def gauge(scrape, name):
    rows = [r.split() for r in scrape.splitlines() if r.split() and r.split()[0] == name]
    if len(rows) != 1 or len(rows[0]) != 2:
        raise ValueError(f'missing/duplicate gauge {name}')
    value = float(rows[0][1])
    if not math.isfinite(value) or value < 0:
        raise ValueError(f'invalid gauge {name}')
    return value


def check_requests(rows, peak_active):
    if len(rows) != 2 or peak_active < 2:
        raise ValueError('two active requests were not observed')
    hashes = set()
    for row in rows:
        if row['prompt_tokens'] != 1_000_000 or row['completion_tokens'] != 64 or row['cached_tokens'] != 0:
            raise ValueError('cold million-token/64-output contract failed')
        hashes.add(row['input_sha256'])
        for key in ('ttft_s', 'elapsed_s', 'decode_span_s'):
            if not math.isfinite(row[key]) or row[key] <= 0:
                raise ValueError('invalid stream timing')
    if len(hashes) != 2:
        raise ValueError('duplicate pressure prompt')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', required=True); p.add_argument('--tokenizer', type=Path, required=True)
    p.add_argument('--run-id', required=True); p.add_argument('--out', type=Path, required=True)
    p.add_argument('--require-capacity-floor', action='store_true',
                   help='Required on the candidate reserve arm; baseline shortfall is recorded separately')
    a = p.parse_args(); base = a.base.rstrip('/')
    def metrics():
        with urllib.request.urlopen(base + '/metrics', timeout=10) as response:
            return response.read().decode()
    before = metrics()
    if a.require_capacity_floor:
        validate_capacity(before)
    for name in ('flare_active_requests', 'flare_http_inflight_requests', 'flare_retiring_request_slots'):
        assert gauge(before, name) == 0, name
    vocab = vocabulary(a.tokenizer)
    bodies = [{'model': 'nvidia/GLM-5.3-Flash-FP4-Local', 'temperature': 1., 'top_p': .95,
               'seed': 531716 + i, 'stream': True, 'stream_options': {'include_usage': True},
               'ignore_eos': True, 'max_tokens': 64,
               'prompt': prompt_ids(vocab, 1_000_000, [a.run_id, 'million-token-pressure', i])}
              for i in range(2)]
    barrier = threading.Barrier(2)
    def send(body):
        barrier.wait(timeout=30)
        row = stream(base, '/v1/completions', body)
        row['input_sha256'] = digest(body)
        return row
    with a.out.open('x') as output:
        def emit(row):
            output.write(json.dumps(row) + '\n'); output.flush()
        emit({'manifest': {'schema': 1, 'run_id': a.run_id, 'length': 1_000_000,
                           'concurrency': 2, 'output_budget': 64, 'ignore_eos': True,
                           'require_capacity_floor': a.require_capacity_floor,
                           'tokenizer_sha256': hashlib.sha256(a.tokenizer.read_bytes()).hexdigest(),
                           'input_sha256': [digest(body) for body in bodies]}, 'metrics_before': before})
        peak = 0
        with ThreadPoolExecutor(2) as pool:
            futures = [pool.submit(send, body) for body in bodies]
            deadline = time.monotonic() + 2400
            while not all(f.done() for f in futures):
                if time.monotonic() > deadline:
                    raise TimeoutError('pressure requests exceeded registered deadline')
                scrape = metrics(); active = gauge(scrape, 'flare_active_requests')
                peak = max(peak, active)
                emit({'time': time.time(), 'active_requests': active,
                      'kv_capacity_tokens': gauge(scrape, 'flare_total_kv_tokens')})
                time.sleep(2)
            rows = [f.result() for f in futures]
        check_requests(rows, peak)
        drain_deadline = time.monotonic() + 60
        while True:
            after = metrics()
            if all(gauge(after, name) == 0 for name in
                   ('flare_active_requests', 'flare_http_inflight_requests', 'flare_retiring_request_slots')):
                break
            if time.monotonic() >= drain_deadline:
                raise TimeoutError('request slots did not drain after both streams completed')
            time.sleep(1)
        if a.require_capacity_floor:
            validate_capacity(after)
        for name in ('flare_active_requests', 'flare_http_inflight_requests', 'flare_retiring_request_slots'):
            assert gauge(after, name) == 0, name
        delta = counter_delta(parse_counters(before, 'flare'), parse_counters(after, 'flare'), 'flare')
        result = {'complete': True, 'requests': rows, 'peak_active_requests': peak,
                  'metrics_after': after, 'speculative_delta': delta,
                  'scope': 'cold concurrent admission and finite completed streams; no retrieval-quality claim'}
        emit(result)
        print(json.dumps({k: v for k, v in result.items() if not k.startswith('metrics_')}), flush=True)


if __name__ == '__main__':
    main()
