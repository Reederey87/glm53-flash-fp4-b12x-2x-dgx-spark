"""Matched mixed-arrival and decode-overlap observations; never decides adoption.

Run balanced and latency with the same run ID on the same native core. Raw SSE
delivery times are retained: a speculative burst is not one token. No raw text.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import math
from pathlib import Path
import threading
import time
import urllib.request

from flare_bench import digest, prompt_ids, stream, vocabulary
from spec_metrics import counter_delta, parse_counters


def summarize(body, start, end, deliveries, usage, done, text_hash):
    if not done or not deliveries or usage is None:
        raise ValueError('incomplete stream or missing timing/usage')
    if type(usage.get('completion_tokens')) is not int or usage['completion_tokens'] != body['max_tokens']:
        raise ValueError('output ended before the registered budget')
    cached = (usage.get('prompt_tokens_details') or {}).get('cached_tokens')
    if type(cached) is not int or cached != 0:
        raise ValueError('mixed benchmark requires observed cold prompts')
    prompt = usage.get('prompt_tokens')
    if type(prompt) is not int or prompt <= 0 or ('prompt' in body and prompt != len(body['prompt'])):
        raise ValueError('prompt usage differs from the exact-token fixture')
    if not (start <= deliveries[0] <= deliveries[-1] <= end):
        raise ValueError('invalid stream timing')
    gaps = [b-a for a, b in zip(deliveries, deliveries[1:])]
    if any(not math.isfinite(x) or x < 0 for x in [start, end, *deliveries, *gaps]):
        raise ValueError('invalid stream timing')
    def percentile(p):
        return sorted(gaps)[math.ceil(len(gaps)*p)-1] if gaps else None
    return {'input_sha256': digest(body), 'output_sha256': text_hash,
            'prompt_tokens': prompt, 'cached_tokens': cached,
            'completion_tokens': usage['completion_tokens'], 'start_s': start, 'end_s': end,
            'ttft_s': deliveries[0]-start, 'elapsed_s': end-start,
            'delivery_times_s': deliveries, 'delivery_gap_p95_s': percentile(.95),
            'delivery_gap_max_s': max(gaps) if gaps else None}


def observe(base, route, body, epoch, ready=None, journal=None):
    start = time.monotonic()-epoch
    usage, done, deliveries = None, False, []
    output_hash = hashlib.sha256()
    request = urllib.request.Request(base+route, json.dumps(body).encode(), {'Content-Type': 'application/json'})
    finish_reasons, error_type = [], None
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            for raw in response:
                line = raw.decode().strip()
                if not line.startswith('data:'):
                    continue
                payload = line[5:].strip()
                if payload == '[DONE]':
                    done = True
                    break
                event = json.loads(payload)
                if 'error' in event:
                    raise ValueError(str(event['error']))
                if event.get('usage'):
                    usage = event['usage']
                pieces = []
                for choice in event.get('choices', []):
                    if choice.get('finish_reason') is not None:
                        finish_reasons.append(choice['finish_reason'])
                    delta = choice.get('delta') or {}
                    pieces.append(choice.get('text') or delta.get('content') or
                                  delta.get('reasoning_content') or delta.get('reasoning') or '')
                piece = ''.join(pieces)
                if piece:
                    deliveries.append(time.monotonic()-epoch)
                    output_hash.update(piece.encode())
                    if ready is not None:
                        ready.set()
    except Exception as error:
        error_type = type(error).__name__
        raise
    finally:
        if journal is not None:
            journal({'input_sha256': digest(body), 'output_sha256': output_hash.hexdigest(),
                     'start_s': start, 'end_s': time.monotonic()-epoch,
                     'delivery_times_s': deliveries, 'usage': usage, 'done': done,
                     'finish_reasons': finish_reasons, 'error_type': error_type})
    return summarize(body, start, time.monotonic()-epoch, deliveries, usage, done, output_hash.hexdigest())


def validate_overlap(rows):
    by_id = {row['id']: row for row in rows}
    prompts = [by_id['long'], by_id['short']]
    begin = min(row['start_s'] for row in prompts)
    end = max(row['end_s'] for row in prompts)
    counts = {}
    for name in ('decode0', 'decode1'):
        row = by_id[name]
        if not row['delivery_times_s'][0] <= begin < row['end_s']:
            raise ValueError('prefill did not arrive during both active decoders')
        count = sum(begin < t < end for t in row['delivery_times_s'])
        if count < 5:
            raise ValueError('insufficient observed decode progress during prompt overlap')
        counts[name] = count
    return {'prompt_interval_s': [begin, end], 'decode_deliveries_during_interval': counts,
            'scope': 'client-visible simultaneous lifetimes/progress; not a GPU dispatch trace'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True)
    parser.add_argument('--policy', required=True, choices=('balanced', 'latency'))
    parser.add_argument('--tokenizer', required=True, type=Path)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--reps', type=int, choices=(1, 3), default=3,
                        help='1 is diagnostic only; performance qualification requires 3')
    args = parser.parse_args()
    base = args.base.rstrip('/')
    vocab = vocabulary(args.tokenizer)
    model = 'nvidia/GLM-5.3-Flash-FP4-Local'
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x') as output:
        def emit(row):
            output.write(json.dumps(row, allow_nan=False)+'\n')
            output.flush()
        emit({'manifest': {'schema': 1, 'policy': args.policy, 'run_id': args.run_id,
              'tokenizer_sha256': hashlib.sha256(args.tokenizer.read_bytes()).hexdigest(),
              'reps': args.reps, 'slot_cap': 4, 'temperature': 1, 'top_p': .95,
              'qualification': 'matched observations; delivery gaps are not per-token gaps'}})
        def make(rep, case, name, length, budget):
            identity = [args.run_id, rep, case, name]
            return {'model': model, 'temperature': 1, 'top_p': .95, 'seed': 20261116+rep,
                    'stream': True, 'stream_options': {'include_usage': True},
                    'prompt': prompt_ids(vocab, length, identity), 'max_tokens': budget}
        warm = make(-1, 'warm', 'warm', 128, 8)
        stream(base, '/v1/completions', warm)
        for rep in range(args.reps):
            for case in ('unequal_burst', 'short_arrivals', 'decode_overlap'):
                items = []
                if case == 'unequal_burst':
                    items = [(str(i), 0, '/v1/completions', make(rep, case, str(i), length, 1))
                             for i, length in enumerate((131072, 32768, 8192, 4096))]
                elif case == 'short_arrivals':
                    items = [('long', 0, '/v1/completions', make(rep, case, 'long', 131072, 1))]
                    items += [(f'short{i}', 2+2*i, '/v1/completions', make(rep, case, f'short{i}', 1024, 1))
                              for i in range(16)]
                else:
                    for i, prompt in enumerate(('Write a detailed account of a voyage across the Pacific Ocean.',
                                                'Write a Python LRU cache with tests and explain its complexity.')):
                        name = f'decode{i}'
                        body = make(rep, case, name, 128, 512)
                        del body['prompt']
                        body['messages'] = [{'role': 'user', 'content':
                            f'Session {digest([args.run_id,rep,case,name])[:24]}. {prompt}'}]
                        items.append((name, 0, '/v1/chat/completions', body))
                    items += [(name, None, '/v1/completions', make(rep, case, name, length, 1))
                              for name, length in (('long', 32768), ('short', 4096))]
                def counters():
                    with urllib.request.urlopen(base+'/metrics', timeout=10) as response:
                        return parse_counters(response.read().decode(), 'flare')
                before = counters()
                epoch = time.monotonic()
                ready = [threading.Event(), threading.Event()]
                def run(item):
                    name, offset, route, body = item
                    if offset is None:
                        for event in ready:
                            if not event.wait(timeout=max(0, 120-(time.monotonic()-epoch))):
                                raise ValueError('decoder first-output prerequisite timed out')
                    else:
                        time.sleep(max(0, epoch+offset-time.monotonic()))
                    row = observe(base, route, body, epoch,
                                  ready[int(name[-1])] if name.startswith('decode') else None)
                    if offset is not None and abs(row['start_s']-offset) > .25:
                        raise ValueError('actual arrival missed the registered offset by over250ms')
                    return {'id': name, 'scheduled_offset_s': offset, **row}
                rows, errors = [], []
                with ThreadPoolExecutor(max_workers=len(items)) as pool:
                    jobs = {pool.submit(run, item): item[0] for item in items}
                    for job in as_completed(jobs):
                        try:
                            row = job.result()
                            rows.append(row)
                            emit({'event': 'request', 'rep': rep, 'case': case, **row})
                        except Exception as error:
                            errors.append({'id': jobs[job], 'error': str(error)})
                            emit({'event': 'request_error', 'rep': rep, 'case': case, **errors[-1]})
                if errors:
                    raise ValueError('mixed benchmark requests failed; partial receipts retained')
                overlap = validate_overlap(rows) if case == 'decode_overlap' else None
                after = counters()
                delta = {name: after[name]-before[name] for name in before}
                if any(value < 0 for value in delta.values()):
                    raise ValueError('native counters reset during mixed workload')
                if case == 'decode_overlap':
                    delta = counter_delta(before, after, 'flare')
                emit({'event': 'case_complete', 'rep': rep, 'case': case,
                      'wall_s': time.monotonic()-epoch, 'request_count': len(rows),
                      'overlap': overlap, 'speculative_delta': delta})
                print(f'{case} rep{rep}: {len(rows)} requests completed', flush=True)
        emit({'complete': True, 'cases': 3*args.reps, 'requests': 25*args.reps})


if __name__ == '__main__':
    main()
