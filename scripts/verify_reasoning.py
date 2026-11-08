#!/usr/bin/env python3
"""Assert the checkpoint template's reasoning contract.

Runs *inside* the engine container (docker exec), where transformers and the
mounted HF snapshot exist. Exits 0 only when:
  * a request that omits reasoning_effort renders "Reasoning Effort: Max"
  * explicit low/high/max render their own level
  * the rendered prompt still starts with [gMASK]<sop>
"""
from __future__ import annotations

import glob
import sys

from transformers import AutoTokenizer

SNAP = glob.glob("/root/.cache/huggingface/hub/models--nvidia--GLM-5.3-Flash-FP4-Local/snapshots/*/")[0]
tok = AutoTokenizer.from_pretrained(SNAP, trust_remote_code=False)
msgs = [{"role": "user", "content": "ping"}]


def render(**kw) -> str:
    return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, **kw)


failures = []
default = render()
if "Reasoning Effort: Max" not in default:
    failures.append(f"default is not Max: {default[:120]!r}")
if not default.startswith("[gMASK]<sop>"):
    failures.append(f"unexpected prefix: {default[:40]!r}")
for level in ("low", "high", "max"):
    text = render(reasoning_effort=level)
    if f"Reasoning Effort: {level.capitalize()}" not in text:
        failures.append(f"explicit {level!r} not honoured: {text[:120]!r}")

if failures:
    print("reasoning contract FAILED: " + "; ".join(failures))
    sys.exit(1)
print("reasoning contract ok: default=Max, explicit low/high/max honoured")
