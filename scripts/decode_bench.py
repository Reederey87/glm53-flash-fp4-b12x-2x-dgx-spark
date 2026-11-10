#!/usr/bin/env python3
"""Repeated decode benchmark for the MTP-depth window (stdlib only).

The full speed matrix (`speed_smoke.py`) is one batch per concurrency: fine as a
smoke, too noisy to decide a 2–12 % decode change. This script runs a fixed
workload at c=1,2,4,8 with N repetitions each, reports the median aggregate and
per-request rates, and records speculative acceptance for the run.

It never gates on its own; `compare_gate.py` applies the pre-registered rule.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import subprocess
import threading
import time
import urllib.request
from datetime import datetime, timezone

SPEC = {
    "accepted": "vllm:spec_decode_num_accepted_tokens_total",
    "draft_tokens": "vllm:spec_decode_num_draft_tokens_total",
    "drafts": "vllm:spec_decode_num_drafts_total",
}
CODE_PROMPT = (
    "Write a Python function `merge_intervals(intervals)` that merges overlapping "
    "closed intervals, handles an empty list, sorts by start, and returns a new list. "
    "Include a short docstring and three doctest examples."
)


def sse(url: str, body: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    t0 = time.perf_counter()
    first = None
    usage: dict = {}
    done = False
    finish = None
    with urllib.request.urlopen(req, timeout=1800) as r:
        for raw in r:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data: "):
                continue
            payload = line[6:]
            if payload == "[DONE]":
                done = True
                break
            try:
                chunk = json.loads(payload)
            except json.JSONDecodeError:
                raise ValueError("invalid SSE JSON")
            if chunk.get("error"):
                raise ValueError(f"stream error: {chunk['error']}")
            if chunk.get("usage"):
                usage = chunk["usage"]
            for ch in chunk.get("choices") or []:
                if ch.get("finish_reason") is not None:
                    finish = ch["finish_reason"]
                delta = ch.get("delta") or {}
                if delta.get("content") or delta.get("reasoning_content") or delta.get("reasoning"):
                    if first is None:
                        first = time.perf_counter()
    end = time.perf_counter()
    count = usage.get("completion_tokens")
    if (not done or finish is None or first is None or not isinstance(count, int)
            or not 0 < count <= body["max_tokens"] or end <= first):
        raise ValueError("incomplete stream, missing usage/timing, or invalid completion length")
    return {"first": first, "end": end, "usage": usage, "done": done,
            "finish_reason": finish, "ttft_s": first - t0}


def metrics(base: str) -> dict:
    out = {}
    try:
        with urllib.request.urlopen(f"{base}/metrics", timeout=10) as r:
            for line in r.read().decode().splitlines():
                if not line or line.startswith("#"):
                    continue
                parts = line.rsplit(" ", 1)
                if len(parts) != 2:
                    continue
                name = parts[0].split("{", 1)[0]
                if name in SPEC.values():
                    try:
                        value = float(parts[1])
                    except ValueError:
                        return {}
                    if not math.isfinite(value) or value < 0:
                        return {}
                    out[name] = out.get(name, 0.0) + value
    except Exception:  # noqa: BLE001
        return {}
    return out if set(out) == set(SPEC.values()) else {}


def engine_identity() -> dict:
    """Host PIDs cover API/engine/ranks even though container PID1 is sleep."""
    result = {}
    for node, command in (
        ("head", ["docker", "top", "vllm_node", "-eo", "pid,args"]),
        ("worker", ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
                    "nvidia@192.168.177.11", "docker", "top", "vllm_node", "-eo", "pid,args"]),
    ):
        output = subprocess.run(command, check=True, capture_output=True, text=True, timeout=15).stdout
        pids = []
        for line in output.splitlines()[1:]:
            fields = line.strip().split(None, 1)
            if len(fields) != 2:
                continue
            pid, argv = fields
            if (argv.startswith("VLLM::EngineCore") or argv.startswith("VLLM::Worker_TP")
                    or ("/usr/local/bin/vllm serve " in argv and "bash" not in argv)):
                pids.append(pid)
        if len(pids) != (3 if node == "head" else 2):
            raise ValueError(f"missing engine/rank processes on {node}")
        result[node] = sorted(pids)
    return result


def one_round(base: str, model: str, conc: int, tokens: int) -> dict:
    out: list[dict] = []
    errs: list[str] = []
    lock = threading.Lock()

    def worker() -> None:
        try:
            r = sse(f"{base}/v1/chat/completions", {
                "model": model,
                "messages": [{"role": "user", "content": CODE_PROMPT}],
                "max_tokens": tokens, "temperature": 0.0, "stream": True,
                "stream_options": {"include_usage": True},
            })
            with lock:
                out.append(r)
        except Exception as exc:  # noqa: BLE001
            with lock:
                errs.append(repr(exc))

    identity0 = engine_identity()
    m0 = metrics(base)
    t0 = time.perf_counter()
    threads = [threading.Thread(target=worker) for _ in range(conc)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    wall = time.perf_counter() - t0
    m1 = metrics(base)
    identity1 = engine_identity()
    if identity0 != identity1:
        errs.append("engine process identity changed during batch")

    completion = sum(((r["usage"] or {}).get("completion_tokens") or 0) for r in out)
    spans = [r["end"] - (r["first"] or r["end"]) for r in out if r["first"]]
    agg = completion / wall if wall else 0.0
    per_req = statistics.mean([c / max(s, 1e-9) for c, s in
                               zip([((r["usage"] or {}).get("completion_tokens") or 0) for r in out], spans)]) \
        if spans else 0.0
    acc = dec = drf = None
    if m0 and m1:
        acc = m1[SPEC["accepted"]] - m0[SPEC["accepted"]]
        dec = m1[SPEC["draft_tokens"]] - m0[SPEC["draft_tokens"]]
        drf = m1[SPEC["drafts"]] - m0[SPEC["drafts"]]
    if (any(v is None or not math.isfinite(v) for v in (acc, dec, drf))
            or not (drf > 0 and dec > 0 and 0 <= acc <= dec)):
        errs.append("missing, reset or invalid speculative-counter deltas")
    return {
        "concurrency": conc, "ok": len(out), "errors": errs,
        "completion_tokens": completion,
        "requests": [{"completion_tokens": r["usage"]["completion_tokens"],
                      "ttft_s": r["ttft_s"], "decode_s": r["end"] - r["first"],
                      "done": r["done"], "finish_reason": r["finish_reason"]} for r in out],
        "metrics_before": m0, "metrics_after": m1,
        "engine_before": identity0, "engine_after": identity1,
        "aggregate_tok_s": round(agg, 3),
        "per_request_tok_s": round(per_req, 3),
        "accepted": acc, "draft_tokens": dec, "drafts": drf,
        "accept_length": round(1 + acc / drf, 4) if acc is not None and drf else None,
        "accept_rate": round(acc / dec, 4) if acc is not None and dec else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--model", default="nvidia/GLM-5.3-Flash-FP4-Local")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--tokens", type=int, default=200)
    ap.add_argument("--concurrency", default="1,2,4,8")
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", default="receipts")
    args = ap.parse_args()
    base = args.base.rstrip("/")
    os.makedirs(args.out, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    result = {"label": args.label, "stamp": stamp, "base": base, "reps": args.reps,
              "tokens": args.tokens, "rounds": [], "medians": {}}

    print(f"[b12x] decode bench {args.label}: {args.reps} reps at c={args.concurrency}")
    sse(f"{base}/v1/chat/completions", {"model": args.model,
        "messages": [{"role": "user", "content": "warmup"}], "max_tokens": 4,
        "temperature": 0.0, "stream": True, "stream_options": {"include_usage": True}})

    for conc in (int(x) for x in args.concurrency.split(",")):
        rounds = []
        for rep in range(args.reps):
            r = one_round(base, args.model, conc, args.tokens)
            r["rep"] = rep
            rounds.append(r)
            print(f"  c={conc} rep{rep}: {r['aggregate_tok_s']} tok/s agg, "
                  f"{r['per_request_tok_s']} per-req, accept_len={r['accept_length']}, "
                  f"accept_rate={r['accept_rate']}, ok={r['ok']}")
        result["rounds"].extend(rounds)
        good = [r for r in rounds if r["errors"] == [] and r["ok"] == conc]
        if not good:
            result["medians"][conc] = None
            continue
        result["medians"][conc] = {
            "aggregate_tok_s": round(statistics.median(r["aggregate_tok_s"] for r in good), 3),
            "per_request_tok_s": round(statistics.median(r["per_request_tok_s"] for r in good), 3),
            "accept_length": round(statistics.median(r["accept_length"] for r in good
                                                      if r["accept_length"] is not None), 4)
            if any(r["accept_length"] is not None for r in good) else None,
            "accept_rate": round(statistics.median(r["accept_rate"] for r in good
                                                    if r["accept_rate"] is not None), 4)
            if any(r["accept_rate"] is not None for r in good) else None,
            "n": len(good),
        }

    path = os.path.join(args.out, f"decode-{args.label}-{stamp}.json")
    with open(path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"[b12x] wrote {path}")
    for conc, m in result["medians"].items():
        print(f"  median c={conc}: {m['aggregate_tok_s'] if m else 'N/A'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
