#!/usr/bin/env bash
set -euo pipefail
cd /probe
uv run --offline --no-project --python /usr/bin/python3 mods/startup-pinned/install.py
exec uv run --offline --no-project --python /usr/bin/python3 scripts/check_kernel_return_cuda.py --mode default
