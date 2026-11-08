#!/usr/bin/env bash
# ============================================================================
# wait_memory.sh — two-node recovery gate
# ============================================================================
# GB10 has no OOM killer and CUDA-free excludes page cache, so the recovery
# condition is MemFree (not just MemAvailable) on both nodes. Exits 0 only when
# head and worker each report MemFree >= 90 GiB and MemAvailable >= 100 GiB.
# Usage: wait_memory.sh [deadline_seconds]
# ============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"
set -a; . "$ENV_FILE"; set +a
: "${WORKER_IP:?WORKER_IP is required}"

DEADLINE="${1:-900}"
FREE_MIN=$((90 * 1024 * 1024))
AVAIL_MIN=$((100 * 1024 * 1024))
END=$((SECONDS + DEADLINE))

probe() {  # $1 = head|worker, $2 = key
    if [ "$1" = head ]; then
        awk -v k="^$2:" '$0 ~ k {print $2}' /proc/meminfo
    else
        timeout 15 ssh -o BatchMode=yes -o ConnectTimeout=5 "$WORKER_IP" \
            "awk -v k='^$2:' '\$0 ~ k {print \$2}' /proc/meminfo" 2>/dev/null
    fi
}

while [ "$SECONDS" -lt "$END" ]; do
    ok=1
    for node in head worker; do
        f="$(probe "$node" MemFree)"; a="$(probe "$node" MemAvailable)"
        if [ "${f:-0}" -lt "$FREE_MIN" ] || [ "${a:-0}" -lt "$AVAIL_MIN" ]; then ok=0; fi
    done
    [ "$ok" -eq 1 ] && {
        printf '[b12x] memory gate: head %s GiB free / %s GiB avail, worker %s GiB free / %s GiB avail\n' \
            "$(($(probe head MemFree) / 1048576))" "$(($(probe head MemAvailable) / 1048576))" \
            "$(($(probe worker MemFree) / 1048576))" "$(($(probe worker MemAvailable) / 1048576))"
        exit 0
    }
    sleep 5
done

printf '[b12x] memory gate not met after %ss: head %s/%s worker %s/%s KiB\n' \
    "$DEADLINE" "$(probe head MemFree)" "$(probe head MemAvailable)" \
    "$(probe worker MemFree)" "$(probe worker MemAvailable)" >&2
exit 1
