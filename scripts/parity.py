#!/usr/bin/env python3
"""Capture and compare temperature-0 outputs across a restart (stdlib only).

Speeding up speculation must not silently change answers. This stores the full
observable response (content, reasoning, tool calls, finish reason, usage) for
three fixed prompts, then compares two captures prompt by prompt.

Usage:
  parity.py --label mtp5
  parity.py --compare receipts/parity-mtp5-*.json receipts/parity-mtp3-*.json

A divergence is reported, not treated as an automatic failure: speculative
decoding changes numerical batch shapes, so greedy text can differ. The review
decides whether the difference is a defect.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

PROMPTS = [
    ("code", "Write a Python function that returns the nth Fibonacci number "
             "iteratively. Include a docstring and two examples."),
    ("math", "A train travels 168 km in 2 hours 20 minutes. What is its average "
             "speed in km/h? Show the steps and give the final number."),
    ("tool", "What is the weather in Reykjavik right now? Use the get_weather tool."),
]
TOOLS = [{"type": "function", "function": {
    "name": "get_weather", "description": "Current weather for a city",
    "parameters": {"type": "object", "properties": {"city": {"type": "string"}},
                   "required": ["city"]}}}]


def post(base: str, body: dict) -> dict:
    req = urllib.request.Request(f"{base}/v1/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=900) as r:
        return json.loads(r.read())


def capture(base: str, model: str, label: str, out: str) -> str:
    rows = []
    for name, prompt in PROMPTS:
        body = {"model": model, "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 512, "temperature": 0.0}
        if name == "tool":
            body["tools"] = TOOLS
            body["tool_choice"] = "auto"
        r = post(base, body)
        msg = r["choices"][0]["message"]
        rows.append({
            "id": name, "prompt": prompt,
            "content": msg.get("content") or "",
            "reasoning": msg.get("reasoning_content") or msg.get("reasoning") or "",
            "tool_calls": msg.get("tool_calls") or [],
            "finish_reason": r["choices"][0].get("finish_reason"),
            "usage": r.get("usage"),
        })
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, f"parity-{label}-{stamp}.json")
    with open(path, "w") as f:
        json.dump({"label": label, "stamp": stamp, "rows": rows}, f, indent=2)
    print(f"[b12x] wrote {path}")
    return path


def compare(a: str, b: str) -> int:
    A = json.load(open(sorted(glob.glob(a))[-1]))
    B = json.load(open(sorted(glob.glob(b))[-1]))
    same = 0
    for ra, rb in zip(A["rows"], B["rows"]):
        eq_c = ra["content"] == rb["content"]
        eq_r = ra["reasoning"] == rb["reasoning"]
        ta = [tc["function"]["name"] for tc in ra["tool_calls"]]
        tb = [tc["function"]["name"] for tc in rb["tool_calls"]]
        eq_t = ta == tb
        same += int(eq_c and eq_r and eq_t)
        print(f"  {ra['id']:5} content={'same' if eq_c else 'DIFF'} "
              f"reasoning={'same' if eq_r else 'DIFF'} tools={'same' if eq_t else 'DIFF'} "
              f"({len(ra['reasoning'])}/{len(rb['reasoning'])} reasoning chars)")
    print(f"[b12x] {same}/{len(A['rows'])} prompts identical across {A['label']} -> {B['label']}")
    return 0 if same == len(A["rows"]) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--model", default="nvidia/GLM-5.3-Flash-FP4-Local")
    ap.add_argument("--label")
    ap.add_argument("--out", default="receipts")
    ap.add_argument("--compare", nargs=2)
    args = ap.parse_args()
    if args.compare:
        return compare(*args.compare)
    if not args.label:
        sys.exit("--label or --compare required")
    capture(args.base.rstrip("/"), args.model, args.label, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
