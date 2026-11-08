#!/usr/bin/env python3
"""Functional acceptance checks for the b12x kit (stdlib only).

Checks, in order:
  models      the served id and max_model_len match the recipe
  thinking    a plain chat returns non-empty reasoning_content (thinking on)
  reasoning   the checkpoint template renders "Reasoning Effort: Max" when the
              request omits reasoning_effort (the kit's default contract)
  tools       a tool request produces a structured tool call
  prefix      a repeated prompt reports cached_tokens > 0

Exit code 0 only when every hard check passes. WARN rows do not fail the run.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"
rows: list[tuple[str, str, str]] = []


def record(status: str, name: str, detail: str) -> None:
    rows.append((status, name, detail))
    print(f"  {status:4}  {name:18} {detail}")


def post(url: str, body: dict, timeout: float = 180.0) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def get(url: str, timeout: float = 10.0) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def chat(base: str, model: str, **kw) -> dict:
    body = {"model": model, "messages": [{"role": "user", "content": "Reply with the single word OK."}],
            "max_tokens": 32, "temperature": 0.0}
    body.update(kw)
    return post(f"{base}/v1/chat/completions", body)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--model", default="nvidia/GLM-5.3-Flash-FP4-Local")
    ap.add_argument("--container", default="vllm_node",
                    help="container used for the in-engine reasoning/template check; '' disables")
    ap.add_argument("--max-model-len", type=int, default=1000000)
    args = ap.parse_args()
    base = args.base.rstrip("/")

    print(f"[b12x] smoke against {base}")

    # models
    try:
        m = get(f"{base}/v1/models")["data"][0]
        if m["id"] != args.model:
            record(FAIL, "models", f"id={m['id']} expected {args.model}")
        elif m.get("max_model_len") != args.max_model_len:
            record(FAIL, "models", f"max_model_len={m.get('max_model_len')} expected {args.max_model_len}")
        else:
            record(PASS, "models", f"{m['id']} @ {m['max_model_len']}")
    except Exception as e:  # noqa: BLE001
        record(FAIL, "models", repr(e))

    # thinking
    try:
        r = chat(base, args.model)
        msg = r["choices"][0]["message"]
        reasoning = msg.get("reasoning_content") or msg.get("reasoning") or ""
        if reasoning.strip():
            record(PASS, "thinking", f"reasoning {len(reasoning)} chars")
        else:
            record(FAIL, "thinking", "no reasoning_content; thinking is off")
    except Exception as e:  # noqa: BLE001
        record(FAIL, "thinking", repr(e))

    # reasoning default (renderer-level, inside the engine container)
    if args.container:
        try:
            here = os.path.dirname(os.path.abspath(__file__))
            subprocess.run(
                ["docker", "cp", os.path.join(here, "verify_reasoning.py"),
                 f"{args.container}:/workspace/verify_reasoning.py"],
                check=True, capture_output=True, timeout=60,
            )
            out = subprocess.run(
                ["docker", "exec", args.container, "python3", "/workspace/verify_reasoning.py"],
                capture_output=True, text=True, timeout=180,
            )
            detail = (out.stdout + out.stderr).strip().splitlines()[-1:] or ["no output"]
            record(PASS if out.returncode == 0 else FAIL, "reasoning-default", detail[0])
        except Exception as e:  # noqa: BLE001
            record(FAIL, "reasoning-default", repr(e))
    else:
        record(WARN, "reasoning-default", "skipped (--container '')")

    # tools
    tools = [{"type": "function", "function": {
        "name": "get_weather",
        "description": "Current weather for a city",
        "parameters": {"type": "object", "properties": {"city": {"type": "string"}},
                       "required": ["city"]},
    }}]
    try:
        r = post(f"{base}/v1/chat/completions", {
            "model": args.model,
            "messages": [{"role": "user", "content": "What is the weather in Reykjavik? Use the tool."}],
            "tools": tools, "tool_choice": "auto", "max_tokens": 256, "temperature": 0.0,
        }, timeout=240)
        msg = r["choices"][0]["message"]
        calls = msg.get("tool_calls") or []
        if calls and calls[0]["function"]["name"] == "get_weather":
            record(PASS, "tools", f"tool_calls={calls[0]['function']['name']} "
                                  f"args={calls[0]['function']['arguments'][:60]}")
        else:
            record(WARN, "tools", f"no tool_call (finish={r['choices'][0].get('finish_reason')})")
    except Exception as e:  # noqa: BLE001
        record(FAIL, "tools", repr(e))

    # prefix cache
    prompt = ("The quick brown fox jumps over the lazy dog. " * 120)[:5000]
    try:
        first = post(f"{base}/v1/chat/completions", {
            "model": args.model, "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 8, "temperature": 0.0,
        })
        second = post(f"{base}/v1/chat/completions", {
            "model": args.model, "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 8, "temperature": 0.0,
        })
        d = (second.get("usage") or {}).get("prompt_tokens_details") or {}
        cached = d.get("cached_tokens")
        if cached is None:
            record(FAIL, "prefix", "cached_tokens not reported")
        elif cached > 0:
            record(PASS, "prefix", f"cached_tokens={cached}")
        else:
            record(FAIL, "prefix", f"cached_tokens=0 (first={ (first.get('usage') or {}).get('prompt_tokens') })")
    except Exception as e:  # noqa: BLE001
        record(FAIL, "prefix", repr(e))

    failed = [r for r in rows if r[0] == FAIL]
    soft = [r for r in rows if r[0] == WARN]
    print(f"[b12x] smoke: {len(rows) - len(failed) - len(soft)}/{len(rows)} checks passed hard"
          f"{'' if not soft else '; warnings: ' + ', '.join(r[1] for r in soft)}"
          f"{'' if not failed else ' — FAILURES: ' + ', '.join(r[1] for r in failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
