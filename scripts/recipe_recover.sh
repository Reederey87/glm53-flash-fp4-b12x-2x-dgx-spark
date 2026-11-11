#!/usr/bin/env bash
# Idempotent recipe-window EXIT/ExecStopPost recovery.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TASK="${1:?window name required}"
[[ "$TASK" =~ ^[a-z0-9-]+$ ]] || exit 2
cd "$ROOT"
. "$ROOT/recipes/windows/$TASK.conf"
RECOVERY_RECIPE="${RECOVERY_RECIPE:-$CONTROL_RECIPE}"
OUT="$ROOT/local/ab-$TASK"
UV=/home/nvidia/.local/bin/uv
mkdir -p "$OUT"
exec 8>"$OUT/recovery.lock"
flock -w 1800 8
[ -e "$OUT/recovery-required" ] || exit 0
failed() {
  status=$?; trap - ERR
  systemctl --user stop vllm-b12x-tailscale.service || true
  if [ "${RECOVERY_GUARD:-0}" = 1 ]; then
    systemctl --user stop vllm-b12x-watchdog.timer vllm-b12x-watchdog.service || true
    systemctl --user stop vllm-b12x.service || true
    systemctl --user stop "b12x-$TASK-recovery-memory.service" || true
  fi
  printf 'recovery failed rc=%s\n' "$status" > "$OUT/recovery-failed.txt" || true
  exit "$status"
}
trap failed ERR
recovery_guard_ok() {
  [ "${RECOVERY_GUARD:-0}" = 1 ] || return 0
  local token stamp invocation age
  [ ! -e "$OUT/recovery-memory.csv.abort" ] || return 1
  systemctl --user is-active --quiet "b12x-$TASK-recovery-memory.service" || return 1
  read -r token stamp < "$OUT/recovery-memory.csv.ready" || return 1
  invocation=$(systemctl --user show "b12x-$TASK-recovery-memory.service" -p InvocationID --value) || return 1
  [ -n "$invocation" ] && [ "$token" = "$invocation" ] || return 1
  [[ "$stamp" =~ ^[0-9]+$ ]] || return 1
  age=$(( $(date +%s) - stamp ))
  [ "$age" -ge 0 ] && [ "$age" -le 20 ]
}
systemctl --user stop vllm-b12x-tailscale.service
systemctl --user stop "b12x-$TASK-memory-a.service" "b12x-$TASK-memory-b.service" || true
systemctl --user stop vllm-b12x.service
if [ "${RECOVERY_GUARD:-0}" = 1 ]; then
  # A safety abort is terminal: ExecStopPost must not start another unguarded
  # recovery after the independent observer stopped one.
  [ ! -e "$OUT/recovery-memory.csv.abort" ]
  [ ! -e "$OUT/recovery-failed.txt" ]
  if ! systemctl --user is-active --quiet "b12x-$TASK-recovery-memory.service"; then
    systemd-run --user --unit="b12x-$TASK-recovery-memory" /bin/bash "$ROOT/scripts/memory_guard.sh" "$OUT/recovery-memory.csv"
  fi
  deadline=$((SECONDS + 30))
  until recovery_guard_ok; do
    [ "$SECONDS" -lt "$deadline" ]
    [ ! -e "$OUT/recovery-memory.csv.abort" ]
    sleep 1
  done
fi
# Fresh A, B and rollback can consume the unit's three-start budget. Reserve
# one bounded recovery reset; ExecStopPost retries never reset it again.
if [ ! -e "$OUT/recovery-reset-used" ]; then
  : > "$OUT/recovery-reset-used"
  systemctl --user reset-failed vllm-b12x.service
fi
printf '\n# --- %s rollback %s ---\n# Restore frozen control recipe/image and default allocator\nRECIPE=%s/%s\nIMAGE_TAG=%s\nB12X_ALLOCATOR_CONF=\n' "$TASK" "$(date -u +%FT%TZ)" "$ROOT" "$RECOVERY_RECIPE" "$CONTROL_IMAGE_TAG" >> .env
systemctl --user start vllm-b12x.service
recovery_guard_ok
for node in head worker; do
  if [ "$node" = head ]; then
    image=$(docker inspect --format '{{.Image}}' vllm_node)
    docker exec -i vllm_node uv run --offline --no-project --python /usr/bin/python3 - < scripts/window_profile.py > "$OUT/$node-rollback.json"
    rank=0
  else
    image=$(ssh nvidia@192.168.177.11 docker inspect --format '{{.Image}}' vllm_node)
    ssh nvidia@192.168.177.11 docker exec -i vllm_node uv run --offline --no-project --python /usr/bin/python3 - < scripts/window_profile.py > "$OUT/$node-rollback.json"
    rank=1
  fi
  [ "$image" = "$CONTROL_IMAGE_ID" ]
  "$UV" run --offline scripts/window_profile.py --check "$OUT/$node-rollback.json" --backend "$CONTROL_BACKEND" --seats "$CONTROL_SEATS" --rank "$rank" --kv "$KV_BYTES"
done
"$UV" run --offline scripts/smoke.py > "$OUT/rollback-smoke.txt" 2>&1
grep -F '5/5 checks passed hard' "$OUT/rollback-smoke.txt"
curl -fsS --max-time 10 http://127.0.0.1:8000/health > "$OUT/rollback-health.txt"
recovery_guard_ok
systemctl --user start vllm-b12x-watchdog.timer
systemctl --user is-active --quiet vllm-b12x.service
systemctl --user is-active --quiet vllm-b12x-watchdog.timer
systemctl --user start vllm-b12x-tailscale.service
for unit in vllm-b12x.service vllm-b12x-watchdog.timer vllm-b12x-tailscale.service; do
  systemctl --user is-active "$unit" >> "$OUT/rollback-units.txt"
done
recovery_guard_ok
if [ "${RECOVERY_GUARD:-0}" = 1 ]; then
  systemctl --user stop "b12x-$TASK-recovery-memory.service"
fi
mv "$OUT/recovery-required" "$OUT/recovery-complete"
date -u +%FT%TZ > "$OUT/recovery-success.txt"
