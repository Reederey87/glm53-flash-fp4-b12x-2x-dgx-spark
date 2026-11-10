"""Exact-token, cache-cold prefill ladder at every concurrency, plus decode.

Uses the deployed tokenizer once per cell outside the measured interval. Raw
completion token IDs give exact lengths; the functional smoke checks chat and
reasoning separately. Arm-specific first tokens prevent prefix reuse, while
seeded payloads and output budgets stay matched. Receipts are saved after each
cell so an interrupted window retains its evidence.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import random
import time
import urllib.request

from decode_bench import one_round
from speed_smoke import WORDS, sse


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-num-seqs", type=int, default=4)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--lengths", default="8192,16384,32768,65536,131072")
    ap.add_argument("--concurrency", default="1,2,4,8")
    ap.add_argument("--refresh-decode-from", help="preserve completed cold prefill; remeasure decode with strict per-request receipts")
    args = ap.parse_args()
    base = args.base.rstrip("/")
    model = "nvidia/GLM-5.3-Flash-FP4-Local"
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    result = {"label": args.label, "max_num_seqs": args.max_num_seqs,
              "decode_budget": 200, "prefill": [], "decode": [], "errors": []}
    if args.refresh_decode_from:
        source = json.loads(Path(args.refresh_decode_from).read_text())
        if (not source.get("complete") or source.get("errors")
                or source["max_num_seqs"] != args.max_num_seqs or source["decode_budget"] != 200):
            raise ValueError("cannot refresh incomplete or unmatched control")
        result["prefill"] = source["prefill"]
        result["prefill_source"] = args.refresh_decode_from

    def save():
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(result, indent=2) + "\n")
        tmp.replace(path)

    def tokenize(prompt):
        req = urllib.request.Request(base + "/tokenize", data=json.dumps({
            "model": model, "prompt": prompt, "add_special_tokens": False,
        }).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as response:
            return json.load(response)["tokens"]

    try:
        sse(base + "/v1/chat/completions", {"model": model,
            "messages": [{"role": "user", "content": "warmup"}], "max_tokens": 4,
            "stream": True, "stream_options": {"include_usage": True}})
        for c in map(int, args.concurrency.split(",")):
            for length in map(int, args.lengths.split(",")):
                if args.refresh_decode_from:
                    continue
                prompts = []
                for i in range(c):
                    rng = random.Random(length * 100 + i)
                    # Label comes first: no shared initial full cache block.
                    text = f"{args.label} c{c} n{length} request{i}. "
                    text += " ".join(rng.choice(WORDS) for _ in range(length))
                    ids = tokenize(text)
                    if len(ids) < length:
                        raise ValueError("tokenizer produced too few tokens")
                    prompts.append(ids[:length])

                def run(ids):
                    r = sse(base + "/v1/completions", {"model": model,
                        "prompt": ids, "max_tokens": 1, "temperature": 0.0,
                        "stream": True, "stream_options": {"include_usage": True}})
                    usage = r["usage"]
                    # Raw completions use choices[].text (handled by sse).
                    ttft = r["first"] - r["t0"] if r["first"] else None
                    cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens")
                    if usage.get("prompt_tokens") != length or cached != 0 or not ttft:
                        raise ValueError(f"invalid cold cell: {usage}, TTFT={ttft}")
                    return {"prompt_tokens": length, "cached_tokens": cached,
                            "ttft_s": ttft, "prefill_tok_s": length / ttft}

                with ThreadPoolExecutor(max_workers=c) as pool:
                    rows = list(pool.map(run, prompts))
                result["prefill"].append({"concurrency": c, "length": length,
                                           "requests": rows})
                save()
                print(f"prefill c={c} n={length}: " + ", ".join(
                    f"{r['prefill_tok_s']:.1f}" for r in rows), flush=True)
            for rep in range(args.reps):
                row = one_round(base, model, c, 200)
                row["rep"] = rep
                result["decode"].append(row)
                save()
                if (row["errors"] or row["ok"] != c or row["completion_tokens"] <= 0
                        or row["accept_rate"] is None or row["accept_length"] is None):
                    raise ValueError(f"invalid decode cell: {row}")
                print(f"decode c={c} rep={rep}: {row}", flush=True)
    except Exception as exc:
        result["errors"].append(repr(exc))
        save()
        raise
    result["complete"] = True
    save()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
