#!/usr/bin/env python3
"""Report how many files referenced by a snapshot's index are missing.

Usage: check_checkpoint.py <snapshot-dir>
Prints the count of missing indexed files and exits non-zero when any is
missing, so callers can gate on it without parsing a path list.
"""
from __future__ import annotations

import json
import os
import sys

if len(sys.argv) != 2:
    print("usage: check_checkpoint.py <snapshot-dir>", file=sys.stderr)
    raise SystemExit(2)

snap = sys.argv[1]
index = os.path.join(snap, "model.safetensors.index.json")
try:
    weight_map = json.load(open(index)).get("weight_map") or {}
except Exception as exc:  # noqa: BLE001
    print(f"cannot read {index}: {exc}", file=sys.stderr)
    raise SystemExit(2)
if not weight_map:
    print(f"{index} has an empty weight_map", file=sys.stderr)
    raise SystemExit(2)

missing = [f for f in sorted(set(weight_map.values()))
           if not os.path.exists(os.path.join(snap, f))]
print(len(missing))
if missing:
    print("missing: " + ", ".join(missing), file=sys.stderr)
    raise SystemExit(1)
