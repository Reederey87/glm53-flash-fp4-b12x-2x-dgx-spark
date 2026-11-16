"""Matched-state observations outside capture; original assertions still decide."""
import hashlib
import json
import os
from pathlib import Path
import time

import torch
import torch.distributed as dist


def digest(value):
    return hashlib.sha256(value.detach().contiguous().cpu().view(torch.uint8).numpy().tobytes()).hexdigest()


def compare(actual, expected, *, output=False):
    a, b = actual.double(), expected.double()
    diff = (a - b).abs()
    bound = .001 + .01 * b.abs() if output else 0
    return {"finite": bool(torch.isfinite(a).all() and torch.isfinite(b).all()),
            "exact": bool(torch.equal(actual, expected)),
            "max_abs": float(diff.max()),
            "relative_l2": float(torch.linalg.vector_norm(a-b) /
                                 torch.linalg.vector_norm(b).clamp_min(1e-30)),
            "outside_original_bounds": int((diff > bound).sum()),
            "elements": a.numel()}


def diagnose(forward, graph, worker, group, device, persistent, initial, output,
             expected_output, stages, expected_stages, source, repetitions):
    path = Path(os.environ["FLARE_LAYER_DIAGNOSTIC_OUT"] + f"-{repetitions}.jsonl")
    observed = {"output": output, **stages}
    expected = {"output": expected_output, **expected_stages}
    saved = {k: v.clone() for k, v in observed.items()}
    saved_state = {k: v.clone() for k, v in persistent.items()}
    source_hash = digest(source)
    first = {}
    first_state = {}
    order = ("eager", "graph", "native", "native", "eager", "graph",
             "graph", "native", "eager")
    try:
        with path.open("x") as out:
            def emit(row):
                out.write(json.dumps(row, allow_nan=False) + "\n")
                out.flush()

            emit({"rank": dist.get_rank(group), "repetitions": repetitions,
                  "scope": "diagnostic only; all original assertions remain",
                  "original_comparison": {
                      k: compare(v, expected[k], output=k == "output")
                      for k, v in saved.items()}})
            for index, kind in enumerate(order):
                for k, value in persistent.items():
                    value.copy_(initial[k])
                torch.cuda.synchronize(device)
                dist.barrier(group=group)
                for _ in range(repetitions):
                    if kind == "eager":
                        forward()
                    elif kind == "graph":
                        graph.replay()
                    else:
                        ticket = worker.submit(0, [])
                        assert ticket is not None
                        deadline = time.monotonic() + 120
                        completion = worker.poll()
                        while completion is None and time.monotonic() < deadline:
                            time.sleep(.001)
                            completion = worker.poll()
                        assert completion is not None and completion.fence == ticket
                torch.cuda.synchronize(device)
                if kind not in first:
                    first[kind] = {k: v.clone() for k, v in observed.items()}
                    first_state[kind] = {k: digest(v) for k, v in persistent.items()}
                hashes = {k: digest(v) for k, v in observed.items()}
                ranks = [None] * dist.get_world_size(group)
                dist.all_gather_object(ranks, hashes, group=group)
                emit({"index": index, "kind": kind, "hashes": hashes,
                      "all_rank_hashes": ranks,
                      "source_unchanged": digest(source) == source_hash,
                      "state_matches_first_same_path": {
                          k: digest(v) == first_state[kind][k]
                          for k, v in persistent.items()},
                      "stages": {k: {
                          "vs_original_eager": compare(v, expected[k], output=k == "output"),
                          "vs_original_native": compare(v, saved[k], output=k == "output"),
                          "vs_first_same_path": compare(v, first[kind][k], output=k == "output")}
                          for k, v in observed.items()}})
            emit({"complete": True, "samples": len(order)})
    finally:
        for k, value in observed.items():
            value.copy_(saved[k])
        for k, value in persistent.items():
            value.copy_(saved_state[k])
        torch.cuda.synchronize(device)
