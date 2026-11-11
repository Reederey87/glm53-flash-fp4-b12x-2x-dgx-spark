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
child=
finish() {
  status=$?; trap - EXIT TERM INT
  if [ "$status" -ne 0 ]; then
    # EXIT also covers errexit inside functions; no dependency on ERR inheritance.
    printf 'recovery failed rc=%s\n' "$status" > "$OUT/recovery-failed.txt" || true
    if [ -n "$child" ]; then
      kill "$child" 2>/dev/null || true
      sleep 1
      kill -KILL "$child" 2>/dev/null || true
      wait "$child" 2>/dev/null || true
    fi
    systemctl --user stop vllm-b12x-tailscale.service || true
    if [ "${RECOVERY_GUARD:-0}" = 1 ]; then
      systemctl --user stop vllm-b12x-watchdog.timer vllm-b12x-watchdog.service || true
      systemctl --user stop vllm-b12x.service || true
      systemctl --user stop "b12x-$TASK-recovery-memory.service" || true
      if [ "${RECOVERY_MODE:-canonical}" = stop-only ]; then
        systemctl --user stop "b12x-$TASK-memory-a.service" "b12x-$TASK-memory-b.service" || true
      fi
    fi
  fi
  exit "$status"
}
trap finish EXIT
trap 'exit 143' TERM
trap 'exit 130' INT
case "${RECOVERY_MODE:-canonical}" in
  stop-only)
    # The original control itself failed its startup floor. This window may
    # restore its ledger/configuration, but must never silently reboot it.
    systemctl --user stop vllm-b12x-watchdog.timer vllm-b12x-watchdog.service vllm-b12x-tailscale.service
    systemctl --user stop vllm-b12x.service
    systemctl --user stop "b12x-$TASK-memory-a.service" "b12x-$TASK-memory-b.service" || true
    for unit in vllm-b12x-watchdog.timer vllm-b12x-watchdog.service vllm-b12x-tailscale.service vllm-b12x.service "b12x-$TASK-memory-a.service" "b12x-$TASK-memory-b.service"; do
      state=$(timeout 5 systemctl --user show "$unit" -p ActiveState --value)
      case "$state" in inactive|failed) ;; *) exit 1 ;; esac
      if [[ "$unit" = *.service ]]; then
        [ "$(timeout 5 systemctl --user show "$unit" -p MainPID --value)" = 0 ]
      fi
    done
    containers=$(timeout 15 docker ps -a --filter 'name=^/vllm_node$' --format '{{.ID}}')
    [ -z "$containers" ]
    containers=$(timeout 20 ssh -n -o ConnectTimeout=5 nvidia@192.168.177.11 docker ps -a --filter 'name=^/vllm_node$' --format '{{.ID}}')
    [ -z "$containers" ]
    printf '\n# --- %s stopped rollback %s ---\n# Canonical configuration restored; unsafe control not restarted\nRECIPE=%s/%s\nIMAGE_TAG=%s\nB12X_ALLOCATOR_CONF=\n' "$TASK" "$(date -u +%FT%TZ)" "$ROOT" "$RECOVERY_RECIPE" "$CONTROL_IMAGE_TAG" >> .env
    mv "$OUT/recovery-required" "$OUT/recovery-complete"
    date -u +%FT%TZ > "$OUT/recovery-stopped.txt"
    exit 0 ;;
  canonical) ;;
  *) exit 2 ;;
esac
recovery_guard_ok() {
  [ "${RECOVERY_GUARD:-0}" = 1 ] || return 0
  local token stamp invocation age
  [ ! -e "$OUT/recovery-memory.csv.abort" ] || return 1
  timeout 5 systemctl --user is-active --quiet "b12x-$TASK-recovery-memory.service" || return 1
  read -r token stamp < "$OUT/recovery-memory.csv.ready" || return 1
  invocation=$(timeout 5 systemctl --user show "b12x-$TASK-recovery-memory.service" -p InvocationID --value) || return 1
  [ -n "$invocation" ] && [ "$token" = "$invocation" ] || return 1
  [[ "$stamp" =~ ^[0-9]+$ ]] || return 1
  age=$(( $(date +%s) - stamp ))
  [ "$age" -ge 0 ] && [ "$age" -le 20 ]
}
checked_run() {
  if [ "${RECOVERY_GUARD:-0}" != 1 ]; then "$@"; return; fi
  recovery_guard_ok
  "$@" <&0 & child=$!
  while kill -0 "$child" 2>/dev/null; do
    recovery_guard_ok
    sleep 2 & wait $!
  done
  local status=0; wait "$child" || status=$?; child=
  [ "$status" -eq 0 ]
  recovery_guard_ok
}
systemctl --user stop vllm-b12x-tailscale.service
systemctl --user stop "b12x-$TASK-memory-a.service" "b12x-$TASK-memory-b.service" || true
systemctl --user stop vllm-b12x.service
if [ "${RECOVERY_GUARD:-0}" = 1 ]; then
  # A failed guarded recovery is terminal, including stale or lost observers.
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
# One bounded reset per recovery, never repeated by ExecStopPost retries.
if [ ! -e "$OUT/recovery-reset-used" ]; then
  : > "$OUT/recovery-reset-used"
  systemctl --user reset-failed vllm-b12x.service
fi
printf '\n# --- %s rollback %s ---\n# Restore frozen control recipe/image and default allocator\nRECIPE=%s/%s\nIMAGE_TAG=%s\nB12X_ALLOCATOR_CONF=\n' "$TASK" "$(date -u +%FT%TZ)" "$ROOT" "$RECOVERY_RECIPE" "$CONTROL_IMAGE_TAG" >> .env
checked_run systemctl --user start vllm-b12x.service
for node in head worker; do
  if [ "$node" = head ]; then
    checked_run timeout 15 docker inspect --format '{{.Image}}' vllm_node > "$OUT/$node-rollback.image"
    checked_run timeout 30 docker exec -i vllm_node uv run --offline --no-project --python /usr/bin/python3 - < scripts/window_profile.py > "$OUT/$node-rollback.json"
    rank=0
    if [ -n "${RECOVERY_LOADER_SHA256:-}" ]; then
      checked_run timeout 15 docker exec vllm_node sha256sum /usr/local/lib/python3.12/dist-packages/vllm/model_executor/model_loader/utils.py > "$OUT/$node-rollback-loader.sha256"
    fi
  else
    checked_run timeout 15 ssh -o ConnectTimeout=5 nvidia@192.168.177.11 docker inspect --format '{{.Image}}' vllm_node > "$OUT/$node-rollback.image"
    checked_run timeout 30 ssh -o ConnectTimeout=5 nvidia@192.168.177.11 docker exec -i vllm_node uv run --offline --no-project --python /usr/bin/python3 - < scripts/window_profile.py > "$OUT/$node-rollback.json"
    rank=1
    if [ -n "${RECOVERY_LOADER_SHA256:-}" ]; then
      checked_run timeout 15 ssh -o ConnectTimeout=5 nvidia@192.168.177.11 docker exec vllm_node sha256sum /usr/local/lib/python3.12/dist-packages/vllm/model_executor/model_loader/utils.py > "$OUT/$node-rollback-loader.sha256"
    fi
  fi
  [ "$(cat "$OUT/$node-rollback.image")" = "$CONTROL_IMAGE_ID" ]
  if [ -n "${RECOVERY_LOADER_SHA256:-}" ]; then
    read -r loader_hash loader_path < "$OUT/$node-rollback-loader.sha256"
    [ "$loader_hash" = "$RECOVERY_LOADER_SHA256" ]
  fi
  checked_run timeout 30 "$UV" run --offline scripts/window_profile.py --check "$OUT/$node-rollback.json" --backend "$CONTROL_BACKEND" --seats "$CONTROL_SEATS" --rank "$rank" --kv "$KV_BYTES"
done
checked_run "$UV" run --offline scripts/smoke.py > "$OUT/rollback-smoke.txt" 2>&1
grep -F '5/5 checks passed hard' "$OUT/rollback-smoke.txt"
checked_run curl -fsS --max-time 10 http://127.0.0.1:8000/health > "$OUT/rollback-health.txt"
recovery_guard_ok
if [ "${RECOVERY_GUARD:-0}" = 1 ]; then
  # Stop joins the observer. Reconcile its terminal result AND abort marker
  # before any access/healing handoff; an abort during stop cannot pass.
  timeout 30 systemctl --user stop "b12x-$TASK-recovery-memory.service"
  timeout 5 systemctl --user show "b12x-$TASK-recovery-memory.service" -p ActiveState -p SubState -p Result -p ExecMainStatus > "$OUT/recovery-observer-terminal.txt"
  grep -qx 'ActiveState=inactive' "$OUT/recovery-observer-terminal.txt"
  grep -qx 'SubState=dead' "$OUT/recovery-observer-terminal.txt"
  grep -qx 'Result=success' "$OUT/recovery-observer-terminal.txt"
  grep -qx 'ExecMainStatus=0' "$OUT/recovery-observer-terminal.txt"
  [ ! -e "$OUT/recovery-memory.csv.abort" ]
fi
systemctl --user is-active --quiet vllm-b12x.service
curl -fsS --max-time 10 http://127.0.0.1:8000/health > "$OUT/rollback-health.txt"
systemctl --user start vllm-b12x-watchdog.timer
systemctl --user is-active --quiet vllm-b12x-watchdog.timer
systemctl --user start vllm-b12x-tailscale.service
for unit in vllm-b12x.service vllm-b12x-watchdog.timer vllm-b12x-tailscale.service; do
  systemctl --user is-active "$unit" >> "$OUT/rollback-units.txt"
done
curl -fsS --max-time 10 http://127.0.0.1:8000/health > "$OUT/rollback-health.txt"
mv "$OUT/recovery-required" "$OUT/recovery-complete"
date -u +%FT%TZ > "$OUT/recovery-success.txt"
