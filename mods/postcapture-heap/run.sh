#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
case "${B12X_POSTCAPTURE_MODE:?explicit reviewed mode required}" in
  observe) exec uv run --offline --no-project --python /usr/bin/python3 "$HERE/install.py" --observe ;;
  trim) exec uv run --offline --no-project --python /usr/bin/python3 "$HERE/install.py" ;;
  *) echo 'unknown postcapture mode' >&2; exit 2 ;;
esac
