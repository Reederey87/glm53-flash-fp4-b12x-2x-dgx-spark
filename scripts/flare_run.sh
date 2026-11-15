#!/usr/bin/env bash
set -euo pipefail
ROOT=/home/nvidia/b12x-flare
source "$ROOT/scripts/flare_env.sh"
exec 9>"$ROOT/local/gpu-operation.lock"
flock -n 9
exec /home/nvidia/.local/bin/uv run --offline --no-project --python /usr/bin/python3 "$ROOT/scripts/flare_run.py" "$@"
