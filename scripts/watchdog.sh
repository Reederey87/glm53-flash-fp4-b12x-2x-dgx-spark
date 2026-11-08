#!/usr/bin/env bash
# ============================================================================
# watchdog.sh — health canary and bounded auto-heal for the b12x serving unit
# ============================================================================
#
# Run by vllm-glm53fp4-watchdog.timer. It does nothing when the serving unit is
# disabled, inactive, activating, or was stopped manually. A healthy /health
# clears the two-tick pending marker. If both ranks are running but /health is
# down, it waits one tick (a long prefill can miss one probe), then restarts
# the unit. Restarts are capped so a broken boot cannot thrash GB10 memory.
#
# The unit's ExecStartPre waits for Docker, the worker, and >=100 GiB
# MemAvailable, so this script deliberately does not gate on free memory while
# the old rank is still holding the pool.
# ============================================================================
set -u

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT="${WATCHDOG_UNIT:-vllm-b12x.service}"
STATE="${WATCHDOG_STATE:-$ROOT/local/watchdog}"
LOG="$STATE/watchdog.log"
STAMPS="$STATE/heal-stamps"
PENDING="$STATE/health-pending"
MAX="${WATCHDOG_MAX_HEALS:-3}"
WINDOW="${WATCHDOG_WINDOW_S:-21600}"
PORT="${PORT:-8000}"
CONTAINER="${CONTAINER_NAME:-vllm_node}"

mkdir -p "$STATE" 2>/dev/null || exit 0
exec 9>"$STATE/lock" || exit 0
flock -n 9 || exit 0

log() { printf '%s %s\n' "$(date -Is)" "$*" >>"$LOG"; }

# Keep the ledger bounded without losing recent decisions.
if [ -f "$LOG" ] && [ "$(wc -c <"$LOG")" -gt 1048576 ]; then
  tail -n 2000 "$LOG" >"$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi

# A manual `systemctl --user stop` leaves the unit inactive; never fight it.
enabled=$(systemctl --user is-enabled "$UNIT" 2>/dev/null || true)
[ "$enabled" = "enabled" ] || exit 0
state=$(systemctl --user show "$UNIT" -p ActiveState --value 2>/dev/null || true)
# A failed unit never becomes active on its own, and systemd refuses new starts
# after StartLimitBurst until reset-failed. That is the state a collided start or
# a boot failure leaves behind, so heal it explicitly under the same bounded cap.
if [ "$state" = "failed" ]; then
  now=$(date +%s)
  touch "$STAMPS"
  heals=$(awk -v now="$now" -v w="$WINDOW" '$1+0 > now-w {c++} END{print c+0}' "$STAMPS")
  if [ "$heals" -ge "$MAX" ]; then
    log "unit failed; heal budget exhausted ($MAX per $(( WINDOW / 3600 ))h), leaving it for a human"
    exit 0
  fi
  echo "$now" >>"$STAMPS"
  log "unit failed; reset-failed and start (heal $(( heals + 1 ))/$MAX)"
  systemctl --user reset-failed "$UNIT" >/dev/null 2>&1 || true
  systemctl --user start --no-block "$UNIT" >/dev/null 2>&1
  exit 0
fi
[ "$state" = "active" ] || exit 0

health=$(curl -sS -o /dev/null -w '%{http_code}' -m 8 "http://127.0.0.1:${PORT}/health" 2>/dev/null || true)
if [ "$health" = "200" ]; then
  rm -f "$PENDING"
  exit 0
fi

# Resolve the worker from the same .env the launcher uses.
WORKER="${WATCHDOG_WORKER:-}"
if [ -z "$WORKER" ] && [ -f "$ROOT/.env" ]; then
  # shellcheck disable=SC1090
  . "$ROOT/.env"
  IFS=',' read -r -a _nodes <<<"${CLUSTER_NODES:-}"
  if [ "${#_nodes[@]}" -gt 1 ]; then
    WORKER="${_nodes[1]}"
  fi
fi
WORKER="${WORKER:-192.168.177.11}"

rank_up() {
  if [ "$1" = "local" ]; then
    docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null || echo false
  else
    # CONTAINER is local config, not user input.
    # shellcheck disable=SC2029
    timeout 20 ssh -o BatchMode=yes -o ConnectTimeout=8 "$WORKER" \
      "docker inspect -f '{{.State.Running}}' $CONTAINER 2>/dev/null" || echo false
  fi
}
r0=$(rank_up local)
r1=$(rank_up remote)

# Both ranks still up: a long prefill can miss one health probe. Wait one tick.
if [ "$r0" = "true" ] && [ "$r1" = "true" ]; then
  if [ ! -f "$PENDING" ]; then
    : >"$PENDING"
    log "health=${health:-curl-error} but both ranks are running; waiting one tick"
    exit 0
  fi
fi
rm -f "$PENDING"

now=$(date +%s)
touch "$STAMPS"
recent=$(awk -v now="$now" -v w="$WINDOW" '$1+0 > now-w {c++} END{print c+0}' "$STAMPS")
if [ "$recent" -ge "$MAX" ]; then
  log "not restarting: ${recent} heals in ${WINDOW}s (cap ${MAX}); r0=$r0 r1=$r1 health=${health:-curl-error}"
  exit 0
fi

echo "$now" >>"$STAMPS"
log "restarting $UNIT: health=${health:-curl-error} r0=$r0 r1=$r1 worker=$WORKER"
# --no-block: a blocking restart lasts ~6 min (the unit's ExecStartPost health
# gate) and outlives this service's start timeout, so every canary run would be
# marked failed even though the restart completed. Fire it and exit clean.
systemctl --user restart --no-block "$UNIT" >>"$LOG" 2>&1
log "restart dispatched (no-block) rc=$?"
