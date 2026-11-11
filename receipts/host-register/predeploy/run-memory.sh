#!/usr/bin/env bash
set -euo pipefail
cd /probe
uv run --offline --no-project --python /usr/bin/python3 mods/startup-pinned/install.py
exec uv run --offline --no-project --python /usr/bin/python3 scripts/check_host_register_memory_cuda.py --mode "${1:?mode required}"
