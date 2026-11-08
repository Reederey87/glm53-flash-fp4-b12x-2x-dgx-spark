#!/usr/bin/env bash
# wait_health.sh — hold the unit in "activating" until /health is 200.
# Usage: wait_health.sh [deadline_seconds]
set -uo pipefail
DEADLINE="${1:-900}"
PORT="${PORT:-8000}"
END=$((SECONDS + DEADLINE))
while [ "$SECONDS" -lt "$END" ]; do
    code="$(curl -s -o /dev/null -w '%{http_code}' -m 3 "http://127.0.0.1:${PORT}/health" 2>/dev/null || true)"
    [ "$code" = 200 ] && exit 0
    sleep 5
done
echo "[b12x] /health not 200 after ${DEADLINE}s" >&2
exit 1
