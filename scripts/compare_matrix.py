"""Compare complete matched matrix receipts; never promote a deployment."""
import argparse
import json
import math
from pathlib import Path
from statistics import median
from decode_bench import SPEC


def validate(receipt):
    if receipt.get("errors") or not receipt.get("complete"):
        raise ValueError("incomplete or failed matrix")
    expected = {(c, n) for c in (1, 2, 4, 8)
                for n in (8192, 16384, 32768, 65536, 131072)}
    cells = {(r["concurrency"], r["length"]) for r in receipt["prefill"]}
    if cells != expected or len(receipt["prefill"]) != 20:
        raise ValueError("missing or duplicate prefill cells")
    for row in receipt["prefill"]:
        if len(row["requests"]) != row["concurrency"]:
            raise ValueError("missing prefill requests")
        if any(r["cached_tokens"] != 0 or r["prompt_tokens"] != row["length"]
               or not all(math.isfinite(r[k]) and r[k] > 0 for k in ("prefill_tok_s", "ttft_s"))
               for r in row["requests"]):
            raise ValueError("invalid or cached prefill")
    for c in (1, 2, 4, 8):
        rows = [r for r in receipt["decode"] if r["concurrency"] == c]
        if len(rows) != 3 or {r["rep"] for r in rows} != {0, 1, 2}:
            raise ValueError("need three decode repetitions")
        for row in rows:
            if (row["errors"] or row["ok"] != c or row["completion_tokens"] <= 0
                    or not row["drafts"] > 0 or not row["draft_tokens"] > 0
                    or not 0 <= row["accepted"] <= row["draft_tokens"]
                    or row["accept_rate"] is None or row["accept_length"] is None):
                raise ValueError("invalid decode cell")
            requests = row.get("requests", [])
            if len(requests) != c or sum(r["completion_tokens"] for r in requests) != row["completion_tokens"]:
                raise ValueError("missing per-request usage")
            for r in requests:
                if (not r["done"] or not r["finish_reason"] or not 0 < r["completion_tokens"] <= receipt["decode_budget"]
                        or not all(math.isfinite(r[k]) and r[k] > 0 for k in ("ttft_s", "decode_s"))):
                    raise ValueError("incomplete request stream")
            if (not 0 <= row["accept_rate"] <= 1 or not 1 <= row["accept_length"] <= 4
                    or not row["aggregate_tok_s"] > 0
                    or not all(math.isfinite(row[k]) for k in ("aggregate_tok_s", "accept_rate", "accept_length", "accepted", "draft_tokens", "drafts"))):
                raise ValueError("invalid acceptance/timing values")
            for snapshot in (row.get("metrics_before", {}), row.get("metrics_after", {})):
                if set(snapshot) != set(SPEC.values()) or not all(math.isfinite(v) and v >= 0 for v in snapshot.values()):
                    raise ValueError("missing or invalid counter snapshot")
            for field, counter in SPEC.items():
                if row[field] != row["metrics_after"][counter] - row["metrics_before"][counter]:
                    raise ValueError("counter delta mismatch")
            if (abs(row["accept_rate"] - row["accepted"] / row["draft_tokens"]) > .0001
                    or abs(row["accept_length"] - (1 + row["accepted"] / row["drafts"])) > .0001):
                raise ValueError("acceptance ratio mismatch")
            identity = row.get("engine_before", {})
            if (identity != row.get("engine_after") or set(identity) != {"head", "worker"}
                    or len(identity["head"]) != 3 or len(identity["worker"]) != 2):
                raise ValueError("missing or changed engine identity")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("baseline")
    ap.add_argument("candidate", nargs="?")
    ap.add_argument("--validate-only", action="store_true")
    args = ap.parse_args()
    if args.validate_only:
        if args.candidate:
            ap.error("validation accepts one receipt")
        validate(json.loads(Path(args.baseline).read_text()))
        print("Complete single-arm operational matrix validated; no comparison or adoption decision.")
        return 0
    if not args.candidate:
        ap.error("comparison requires two receipts")
    a, b = [json.loads(Path(p).read_text()) for p in (args.baseline, args.candidate)]
    for receipt in (a, b):
        validate(receipt)
    for key in ("max_num_seqs", "decode_budget"):
        if a[key] != b[key]:
            raise ValueError(f"unmatched control: {key}")
    rows = []
    for ar in a["prefill"]:
        c, n = ar["concurrency"], ar["length"]
        br = next(r for r in b["prefill"] if (r["concurrency"], r["length"]) == (c, n))
        av, bv = [median(r["prefill_tok_s"] for r in x["requests"]) for x in (ar, br)]
        rows.append((f"prefill c{c} {n}", av, bv))
    for c in (1, 2, 4, 8):
        aa, bb = [[r for r in x["decode"] if r["concurrency"] == c] for x in (a, b)]
        if sorted(r["completion_tokens"] for r in aa) != sorted(r["completion_tokens"] for r in bb):
            raise ValueError(f"unmatched actual decode lengths at c{c}")
        if sorted(r["completion_tokens"] for row in aa for r in row["requests"]) != sorted(r["completion_tokens"] for row in bb for r in row["requests"]):
            raise ValueError(f"unmatched per-request decode lengths at c{c}")
        for metric in ("aggregate_tok_s", "accept_rate", "accept_length"):
            rows.append((f"{metric} c{c}", median(r[metric] for r in aa),
                         median(r[metric] for r in bb)))
    print("| metric | control | candidate | change |\n|---|---:|---:|---:|")
    regressions = []
    for name, av, bv in rows:
        change = (bv / av - 1) * 100 if av else None
        if change is None:
            raise ValueError(f"zero denominator: {name}")
        print(f"| {name} | {av:.4f} | {bv:.4f} | {change:+.2f}% |")
        if change < -2:
            regressions.append(name)
    print("\n" + ("REPEAT flagged cells before judging a robust regression: " + ", ".join(regressions)
                   if regressions else "Speed guards passed; review memory and functional receipts before adoption."))
    return 3 if regressions else 0


if __name__ == "__main__":
    raise SystemExit(main())
