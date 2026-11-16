"""Post-replay diagnostics; never runs inside the compiled graph or changes bounds."""
import hashlib
import json
import os
from pathlib import Path
import time

import torch
import torch.distributed as dist


def compare(actual, expected):
    a, b = actual.double(), expected.double()
    diff = (a-b).abs()
    return {'finite': bool(torch.isfinite(a).all() and torch.isfinite(b).all()),
            'max_abs': float(diff.max()),
            'relative_l2': float(torch.linalg.vector_norm(a-b) / torch.linalg.vector_norm(b).clamp_min(1e-30)),
            'outside_original_bounds': int((diff > .001 + .01*b.abs()).sum()),
            'elements': a.numel(), 'exact': bool(torch.equal(actual, expected))}


def diagnose(forward, worker, group, device, persistent, initial, output,
             expected_output, repetitions):
    destination = Path(os.environ['FLARE_LAYER_DIAGNOSTIC_OUT'] + f'-{repetitions}.jsonl')
    saved_output = output.clone()
    saved_state = {k: v.clone() for k, v in persistent.items()}
    first = {}
    try:
        with destination.open('x') as out:
            def emit(row):
                out.write(json.dumps(row, allow_nan=False)+'\n'); out.flush()
            emit({'original_comparison': compare(saved_output, expected_output),
                  'rank': dist.get_rank(group), 'repetitions': repetitions,
                  'scope': 'diagnostic only; original assertion remains mandatory'})
            for index, kind in enumerate(('eager', 'native', 'native', 'eager', 'eager', 'native')):
                for k, value in persistent.items():
                    value.copy_(initial[k])
                torch.cuda.synchronize(device)
                dist.barrier(group=group)
                for _ in range(repetitions):
                    if kind == 'eager':
                        forward()
                    else:
                        ticket = worker.submit(0, [])
                        assert ticket is not None
                        deadline = time.monotonic()+120
                        completion = worker.poll()
                        while completion is None and time.monotonic() < deadline:
                            time.sleep(.001); completion = worker.poll()
                        assert completion is not None and completion.fence == ticket
                torch.cuda.synchronize(device)
                actual = output.clone()
                first.setdefault(kind, actual)
                digest = hashlib.sha256(actual.cpu().view(torch.uint8).numpy().tobytes()).hexdigest()
                ranks = [None] * dist.get_world_size(group)
                dist.all_gather_object(ranks, digest, group=group)
                emit({'index': index, 'kind': kind, 'output_sha256': digest,
                      'all_rank_hashes': ranks,
                      'vs_original_eager': compare(actual, expected_output),
                      'vs_original_native': compare(actual, saved_output),
                      'vs_first_same_path': compare(actual, first[kind])})
            emit({'complete': True, 'samples': 6})
    finally:
        output.copy_(saved_output)
        for k, value in persistent.items():
            value.copy_(saved_state[k])
        torch.cuda.synchronize(device)
