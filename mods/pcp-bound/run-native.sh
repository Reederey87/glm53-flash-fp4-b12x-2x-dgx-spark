#!/usr/bin/env bash
set -euo pipefail
cd /probe
uv run --offline --no-project --python /usr/bin/python3 mods/startup-pinned/install.py
uv run --offline --no-project --python /usr/bin/python3 mods/native-ownership/install.py
exec uv run --offline --no-project --python /usr/bin/python3 scripts/check_pcp_native_cuda.py \
 --device-spelling "${1:?spelling required}" --run-id "${2:?run id required}" --node "${3:?node required}"
