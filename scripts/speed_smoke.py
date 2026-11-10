#!/usr/bin/env python3
"""Speed smoke for the b12x kit (stdlib only).

Matrix required by AGENTS.md:
  * prefill with unique, cache-cold prompts at 8k, 16k, 32k, 64k, 128k tokens
  * decode at concurrency 1, 2, 4, 8 with a fixed 200-token budget
  * speculative-decoding acceptance from the /metrics deltas of that run

`--gate` also enforces the thresholds in docs/03-gate.md and exits non-zero on
any request error, missing acceptance counters, or threshold miss.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import threading
import time
import urllib.request
from datetime import datetime, timezone

WORDS = ("harbor lantern velvet copper meadow signal archive orbit marrow glacier "
         "timber cascade falcon ember lattice quartz ripple summit tungsten willow").split()

SPEC = {
    "accepted": "vllm:spec_decode_num_accepted_tokens_total",
    "draft_tokens": "vllm:spec_decode_num_draft_tokens_total",
    "drafts": "vllm:spec_decode_num_drafts_total",
}


def make_prompt(tokens: int) -> str:
    """Cache-cold prompt: a per-request nonce makes the first tokens unique."""
    rng = random.Random()
    nonce = os.urandom(8).hex()
    return f"Request {nonce}. " + " ".join(
        rng.choice(WORDS) for _ in range(int(tokens / 1.3) + 8))


def sse(url: str, body: dict) -> dict:
    """POST a streaming completion; timestamp the first generated token."""
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    t0 = time.perf_counter()
    first = None
    usage: dict = {}
    chunks = 0
    with urllib.request.urlopen(req, timeout=1800) as r:
        for raw in r:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data: "):
                continue
            payload = line[6:]
            if payload == "[DONE]":
                break
            try:
                chunk = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if chunk.get("usage"):
                usage = chunk["usage"]
            for ch in chunk.get("choices") or []:
                delta = ch.get("delta") or {}
                piece = delta.get("content") or delta.get("reasoning_content") \
                    or delta.get("reasoning") or ch.get("text")
                if piece:
                    chunks += 1
                    if first is None:
                        first = time.perf_counter()
        end = time.perf_counter()
    return {"t0": t0, "first": first, "end": end, "usage": usage, "chunks": chunks}


def metrics(base: str) -> dict:
    out = {v: 0.0 for v in SPEC.values()}
    try:
        with urllib.request.urlopen(f"{base}/metrics", timeout=10) as r:
            for line in r.read().decode().splitlines():
                if not line or line.startswith("#"):
                    continue
                parts = line.rsplit(" ", 1)
                if len(parts) != 2:
                    continue
                head, value = parts
                name = head.split("{", 1)[0]
                if name in out:
                    try:
                        out[name] += float(value)
                    except ValueError:
                        pass
    except Exception:  # noqa: BLE001
        return {}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--model", default="nvidia/GLM-5.3-Flash-FP4-Local")
    ap.add_argument("--out", default="receipts")
    ap.add_argument("--lengths", default="8192,16384,32768,65536,131072")
    ap.add_argument("--decode-tokens", type=int, default=200)
    ap.add_argument("--concurrency", default="1,2,4,8")
    ap.add_argument("--gate", action="store_true")
    args = ap.parse_args()
    base = args.base.rstrip("/")
    os.makedirs(args.out, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    result = {"stamp": stamp, "model": args.model, "base": base,
              "prefill": [], "decode": [], "errors": []}
    failed = False

    def fail(msg: str) -> None:
        nonlocal failed
        failed = True
        result["errors"].append(msg)
        print(f"  ERROR {msg}")

    print("[b12x] warmup")
    sse(f"{base}/v1/chat/completions", {
        "model": args.model, "messages": [{"role": "user", "content": "warmup"}],
        "max_tokens": 4, "temperature": 0.0, "stream": True,
        "stream_options": {"include_usage": True}})

    for i, length in enumerate(int(x) for x in args.lengths.split(",")):
        r = sse(f"{base}/v1/chat/completions", {
            "model": args.model, "messages": [{"role": "user", "content": make_prompt(length)}],
            "max_tokens": 1, "temperature": 0.0, "stream": True,
            "stream_options": {"include_usage": True}})
        usage = r["usage"] or {}
        cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0) or 0
        pt = usage.get("prompt_tokens")
        ttft = (r["first"] - r["t0"]) if r["first"] else None
        row = {"requested": length, "tokens": pt, "cached_tokens": cached,
               "ttft_s": round(ttft, 4) if ttft else None,
               "prefill_tok_s": round(pt / ttft, 1) if (pt and ttft) else None}
        if cached:
            fail(f"prefill {pt}: {cached} prompt tokens were cache hits; prompt is not cold")
        if not pt:
            fail(f"prefill {length}: usage.prompt_tokens missing")
        result["prefill"].append(row)
        if not ttft:
            fail(f"prefill {pt}: no token received")
        print(f"  prefill {pt:>7} tok  TTFT {ttft if ttft else float('nan'):7.3f}s"
              f"  {row['prefill_tok_s']} tok/s")

    for c in (int(x) for x in args.concurrency.split(",")):
        out: list[dict] = []
        errs: list[str] = []
        lock = threading.Lock()

        def worker() -> None:
            body = {"model": args.model,
                    "messages": [{"role": "user", "content": "Write about the sea."}],
                    "max_tokens": args.decode_tokens, "temperature": 0.0, "stream": True,
                    "stream_options": {"include_usage": True}}
            try:
                r = sse(f"{base}/v1/chat/completions", body)
                with lock:
                    out.append(r)
            except Exception as e:  # noqa: BLE001
                with lock:
                    errs.append(repr(e))

        m0 = metrics(base)
        t0 = time.perf_counter()
        threads = [threading.Thread(target=worker) for _ in range(c)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        wall = time.perf_counter() - t0
        m1 = metrics(base)

        completion = sum(((r["usage"] or {}).get("completion_tokens") or 0) for r in out)
        spans = [r["end"] - (r["first"] or r["end"]) for r in out if r["first"]]
        gen_time = sum(spans) / max(len(spans), 1)
        for e in errs:
            fail(f"c={c}: {e}")
        if len(out) != c:
            fail(f"c={c}: {len(out)}/{c} requests completed")
        if out and (completion == 0 or not spans):
            fail(f"c={c}: no completion tokens or no first-token timestamp")

        acc = dec = drf = None
        if m0 and m1:
            d = {k: m1.get(v, 0) - m0.get(v, 0) for k, v in SPEC.items()}
            acc, dec, drf = d["accepted"], d["draft_tokens"], d["drafts"]
            if drf <= 0 or dec <= 0:
                fail(f"c={c}: spec-decode counters did not advance (drafts={drf}, draft_tokens={dec})")
                acc = dec = drf = None
        else:
            fail(f"c={c}: /metrics unavailable")

        row = {
            "concurrency": c,
            "requests_ok": len(out),
            "decode_length": completion,
            "wall_s": round(wall, 2),
            "aggregate_tok_s": round(completion / wall, 2) if wall else None,
            "mean_decode_tok_s": round(completion / max(gen_time * len(out), 1e-9), 2) if out and gen_time else None,
            "accepted_tokens": acc, "draft_tokens": dec, "drafts": drf,
            "acceptance_length": round(1 + acc / drf, 3) if drf else None,
            "draft_accept_rate": round(acc / dec, 3) if dec else None,
        }
        result["decode"].append(row)
        print(f"  decode c={c}  {row['aggregate_tok_s']} tok/s  len={completion}"
              f"  accept_len={row['acceptance_length']}  accept_rate={row['draft_accept_rate']}")

    # --- gate -----------------------------------------------------------------
    if args.gate:
        pre = {r["tokens"]: r["prefill_tok_s"] for r in result["prefill"]}
        c1 = next((r for r in result["decode"] if r["concurrency"] == 1), None)
        c8 = next((r for r in result["decode"] if r["concurrency"] == 8), None)
        required = [8192, 16384, 32768, 65536, 131072]
        got = sorted(r["requested"] for r in result["prefill"])
        checks_ladder = got == required
        smallest = pre[min(pre)] if pre else 0
        largest_key = max(pre) if pre else 0
        largest = pre.get(largest_key) or 0
        checks = [
            ("prefill ladder is exactly 8k..128k", checks_ladder),
            ("prefill smallest point >= 1500", (smallest or 0) >= 1500),
            ("prefill largest point >= 1500", (largest or 0) >= 1500),
            ("decode c1 >= 25", bool(c1 and (c1["aggregate_tok_s"] or 0) >= 25)),
            ("decode c8 >= 55", bool(c8 and (c8["aggregate_tok_s"] or 0) >= 55)),
            ("accept len >= 2.0", all((r["acceptance_length"] or 0) >= 2.0 for r in result["decode"])),
            ("accept rate >= 0.25", all((r["draft_accept_rate"] or 0) >= 0.25 for r in result["decode"])),
        ]
        result["gate"] = {name: bool(ok) for name, ok in checks}
        for name, ok in checks:
            print(f"  {'PASS' if ok else 'FAIL'}  {name}")
            if not ok:
                failed = True

    result["failed"] = failed
    js = os.path.join(args.out, f"speed-{stamp}.json")
    md = os.path.join(args.out, f"speed-{stamp}.md")
    with open(js, "w") as f:
        json.dump(result, f, indent=2)
    with open(md, "w") as f:
        f.write(f"# Speed smoke — {stamp}\n\n`{args.model}` at `{base}`\n\n## Prefill (cache-cold)\n\n")
        f.write("| tokens | TTFT s | prefill tok/s |\n|---:|---:|---:|\n")
        for r in result["prefill"]:
            f.write(f"| {r['tokens']} | {r['ttft_s']} | {r['prefill_tok_s']} |\n")
        f.write("\n## Decode (200-token budget)\n\n")
        f.write("| conc | ok | decode tokens | aggregate tok/s | accept len | accept rate |\n")
        f.write("|---:|---:|---:|---:|---:|---:|\n")
        for r in result["decode"]:
            f.write(f"| {r['concurrency']} | {r['requests_ok']} | {r['decode_length']} | "
                    f"{r['aggregate_tok_s']} | {r['acceptance_length']} | {r['draft_accept_rate']} |\n")
        if result["errors"]:
            f.write("\n## Errors\n\n" + "\n".join(f"- {e}" for e in result["errors"]) + "\n")
    print(f"[b12x] wrote {js}\n[b12x] wrote {md}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
