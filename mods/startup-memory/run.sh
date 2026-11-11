#!/usr/bin/env bash
# Applied by the pinned upstream launcher to both fresh containers before serve.
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec uv run --offline --no-project --python /usr/bin/python3 "$HERE/install.py"
