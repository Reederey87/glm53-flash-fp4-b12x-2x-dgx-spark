#!/usr/bin/env python3
"""Apply the pre-registered MTP-depth decision rule to two decode receipts.

Usage: compare_gate.py --baseline decode-mtp5-*.json --candidate decode-mtp3-*.json

Prints per-concurrency deltas and a verdict:
  ADOPT        primary concurrency >= +5 % and no guard breached
  INCONCLUSIVE  primary between +2 % and +5 %, no guard breached
  REVERT       below +2 %, or a guard breached
Acceptance length is diagnostic (its maximum is 1+k, so k=3 cannot reach k=5's
ceiling); the acceptance *rate* has a sanity floor only.
"""
from __future__ import annotations

import argparse
import glob
import json
import sys


def load(pattern: str) -> dict:
    files = sorted(glob.glob(pattern))
    if not files:
        sys.exit(f"no receipt matches {pattern}")
    with open(files[-1]) as f:
        return json.load(f)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--primary", default="1,8")
    ap.add_argument("--adopt-pct", type=float, default=5.0)
    ap.add_argument("--inconclusive-pct", type=float, default=2.0)
    ap.add_argument("--regression-pct", type=float, default=-5.0)
    ap.add_argument("--accept-floor", type=float, default=0.20)
    args = ap.parse_args()

    b = load(args.baseline)
    c = load(args.candidate)
    print(f"baseline : {b['label']} ({b['stamp']}) reps={b['reps']}")
    print(f"candidate: {c['label']} ({c['stamp']}) reps={c['reps']}")
    print(f"{'conc':>4} {'base agg':>10} {'cand agg':>10} {'delta':>8} "
          f"{'base/re':>9} {'cand/re':>9} {'delta':>8}")
    deltas = {}
    for k in sorted({int(x) for x in b["medians"]} & {int(x) for x in c["medians"]}):
        bm, cm = b["medians"][str(k)], c["medians"][str(k)]
        if not bm or not cm:
            print(f"{k:>4} {'N/A':>10} {'N/A':>10}")
            continue
        da = (cm["aggregate_tok_s"] / bm["aggregate_tok_s"] - 1) * 100 if bm["aggregate_tok_s"] else 0
        dp = (cm["per_request_tok_s"] / bm["per_request_tok_s"] - 1) * 100 if bm["per_request_tok_s"] else 0
        deltas[k] = {"aggregate": da, "per_request": dp,
                     "accept_rate": cm.get("accept_rate"), "accept_length": cm.get("accept_length")}
        print(f"{k:>4} {bm['aggregate_tok_s']:>10} {cm['aggregate_tok_s']:>10} {da:>7.2f}% "
              f"{bm['per_request_tok_s']:>9} {cm['per_request_tok_s']:>9} {dp:>7.2f}%")

    primary = [int(x) for x in args.primary.split(",") if int(x) in deltas]
    if not primary:
        print("VERDICT: REVERT (no primary concurrency measured)")
        return 2
    best = max(deltas[k]["aggregate"] for k in primary)
    guards = [(k, v) for k, v in deltas.items()
              if k not in primary and v["aggregate"] < args.regression_pct]
    low_accept = [(k, v["accept_rate"]) for k, v in deltas.items()
                  if v["accept_rate"] is not None and v["accept_rate"] < args.accept_floor]

    print(f"\nprimary c={primary}: best aggregate delta {best:+.2f}%")
    for k, rate in [(k, v.get("accept_rate")) for k, v in deltas.items()]:
        print(f"  c={k}: accept_rate={rate} accept_length={deltas[k].get('accept_length')}")
    if guards:
        print(f"GUARD BREACH (non-primary regression < {args.regression_pct}%): {guards}")
    if low_accept:
        print(f"GUARD BREACH (accept_rate < {args.accept_floor}): {low_accept}")

    if guards or low_accept:
        print("VERDICT: REVERT")
        return 2
    if best >= args.adopt_pct:
        print("VERDICT: ADOPT")
        return 0
    if best >= args.inconclusive_pct:
        print("VERDICT: INCONCLUSIVE (repeat before adopting)")
        return 3
    print("VERDICT: REVERT")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
