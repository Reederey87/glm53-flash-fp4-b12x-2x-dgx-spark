"""Matched exact-token cold-prefill and decode matrix for native Flare and vLLM.

Uses raw IDs for prefill and reports observed cache use; missing evidence fails.
The same tokenizer, seed and arguments must be used on both arms. This collects
evidence; it does not make an adoption decision.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import random
import threading
import time
import urllib.request

from spec_metrics import counter_delta, parse_counters


def digest(value):
    return hashlib.sha256(json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def vocabulary(tokenizer):
    doc = json.loads(Path(tokenizer).read_text())
    special = {t["id"] for t in doc.get("added_tokens", []) if t.get("special")}
    vocab = doc["model"]["vocab"]
    pairs = vocab.items() if isinstance(vocab, dict) else ((v[0], i) for i, v in enumerate(vocab))
    ids = [i for token, i in pairs if i not in special and token.startswith(("Ġ", "▁"))
           and token[1:].isascii() and token[1:].isalpha() and 3 <= len(token[1:]) <= 12]
    if len(ids) < 256:
        raise ValueError("insufficient ordinary word tokens in pinned tokenizer")
    return sorted(set(ids))


def prompt_ids(vocab, length, identity):
    rng = random.Random(digest(identity))
    return rng.choices(vocab, k=length)


def stream(base, route, body):
    request = urllib.request.Request(base + route, json.dumps(body).encode(), {"Content-Type": "application/json"})
    start = time.perf_counter()
    first = None
    usage = None
    text = []
    done = False
    with urllib.request.urlopen(request, timeout=1800) as response:
        for raw in response:
            line = raw.decode().strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                done = True
                break
            chunk = json.loads(payload)
            if "error" in chunk:
                raise ValueError(str(chunk["error"]))
            if chunk.get("usage"):
                usage = chunk["usage"]
            for choice in chunk.get("choices", []):
                delta = choice.get("delta") or {}
                piece = choice.get("text") or delta.get("content") or delta.get("reasoning_content") or delta.get("reasoning")
                if piece:
                    if first is None:
                        first = time.perf_counter()
                    text.append(piece)
    end = time.perf_counter()
    if not done or first is None or not usage or not usage.get("completion_tokens"):
        raise ValueError("incomplete stream, output or usage evidence")
    cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens")
    if type(cached) is not int or cached < 0:
        raise ValueError("cached-token observation missing or invalid")
    span = end - first
    return {"prompt_tokens": usage["prompt_tokens"], "cached_tokens": cached,
            "completion_tokens": usage["completion_tokens"], "ttft_s": first - start,
            "elapsed_s": end - start, "decode_span_s": span,
            "decode_tok_s": usage["completion_tokens"] / span if span > 0 else None,
            "output_sha256": hashlib.sha256("".join(text).encode()).hexdigest()}


def validate_prefill(rows, length):
    if any(row["prompt_tokens"] != length or row["cached_tokens"] != 0 for row in rows):
        raise ValueError("prefill exact-length or observed cold-cache contract failed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--engine", choices=("vllm", "flare"), required=True)
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", default="nvidia/GLM-5.3-Flash-FP4-Local")
    parser.add_argument("--reps", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20261115)
    parser.add_argument("--lengths", default="8192,16384,32768,65536,131072")
    parser.add_argument("--concurrency", default="1,2,4,8")
    parser.add_argument("--decode-tokens", type=int, default=200)
    parser.add_argument("--slot-cap", type=int, default=4)
    args = parser.parse_args()
    args.base = args.base.rstrip("/")
    if args.reps < 1 or args.decode_tokens < 2:
        parser.error("positive reps and decode budget >=2 required")
    vocab = vocabulary(args.tokenizer)
    manifest = {"schema": 1, "engine": args.engine, "seed": args.seed,
                "tokenizer_sha256": hashlib.sha256(args.tokenizer.read_bytes()).hexdigest(),
                "temperature": 1.0, "top_p": 0.95, "slot_cap": args.slot_cap,
                "reps": args.reps, "decode_budget": args.decode_tokens,
                "decode_rate_definition": "completion_tokens / (stream_end - first_output); includes first burst",
                "qualification": "measurement only; no adoption decision"}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as output:
        output.write(json.dumps({"manifest": manifest}) + "\n")
        output.flush()

        def body(seed):
            return {"model": args.model, "temperature": 1.0, "top_p": 0.95, "seed": seed,
                    "stream": True, "stream_options": {"include_usage": True}}

        warm = body(args.seed)
        warm.update(prompt=prompt_ids(vocab, 128, [args.seed, "warm"]), max_tokens=8)
        stream(args.base, "/v1/completions", warm)

        def batch(route, bodies):
            barrier = threading.Barrier(len(bodies))

            def worker(item):
                barrier.wait(timeout=30)
                row = stream(args.base, route, item)
                row["input_sha256"] = digest(item)
                return row

            start = time.perf_counter()
            with ThreadPoolExecutor(max_workers=len(bodies)) as pool:
                rows = list(pool.map(worker, bodies))
            return rows, time.perf_counter() - start

        def emit(row):
            output.write(json.dumps(row) + "\n")
            output.flush()
            print(json.dumps({k: v for k, v in row.items() if k != "requests"}), flush=True)

        def metrics():
            with urllib.request.urlopen(args.base + "/metrics", timeout=10) as response:
                return parse_counters(response.read().decode(), args.engine)

        for rep in range(args.reps):
            for concurrency in map(int, args.concurrency.split(",")):
                for length in map(int, args.lengths.split(",")):
                    bodies = []
                    for i in range(concurrency):
                        item = body(args.seed + i)
                        item.update(prompt=prompt_ids(vocab, length, [args.seed, rep, concurrency, length, i]), max_tokens=1)
                        bodies.append(item)
                    rows, wall = batch("/v1/completions", bodies)
                    validate_prefill(rows, length)
                    for row in rows:
                        row["prefill_tok_s"] = row["prompt_tokens"] / row["ttft_s"]
                    emit({"kind": "prefill", "rep": rep, "concurrency": concurrency,
                          "length": length, "slot_cap": args.slot_cap, "wall_s": wall, "requests": rows})
                for task, prompt in (("prose", "Write a detailed account of a voyage across the Pacific Ocean."),
                                     ("code", "Write a Python LRU cache with tests and explain its complexity.")):
                    bodies = []
                    for i in range(concurrency):
                        item = body(args.seed + i)
                        nonce = digest([args.seed, rep, concurrency, task, i])[:24]
                        item.update(messages=[{"role": "user", "content": f"Session {nonce}. {prompt}"}], max_tokens=args.decode_tokens)
                        bodies.append(item)
                    before = metrics()
                    rows, wall = batch("/v1/chat/completions", bodies)
                    delta = counter_delta(before, metrics(), args.engine)
                    emit({"kind": "decode", "task": task, "rep": rep, "concurrency": concurrency,
                          "slot_cap": args.slot_cap, "wall_s": wall, "requests": rows,
                          "aggregate_tok_s": sum(r["completion_tokens"] for r in rows) / wall,
                          "speculative_delta": delta,
                          "acceptance_length": 1 + delta["accepted"] / delta["drafts"],
                          "draft_accept_rate": delta["accepted"] / delta["draft_tokens"]})


if __name__ == "__main__":
    main()
