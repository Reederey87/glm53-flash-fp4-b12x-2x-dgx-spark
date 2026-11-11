#!/usr/bin/env bash
# Idempotent recipe-window EXIT/ExecStopPost recovery.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TASK="${1:?window name required}"
[[ "$TASK" =~ ^[a-z0-9-]+$ ]] || exit 2
cd "$ROOT"
. "$ROOT/recipes/windows/$TASK.conf"
OUT="$ROOT/local/ab-$TASK"
UV=/home/nvidia/.local/bin/uv
mkdir -p "$OUT"
exec 8>"$OUT/recovery.lock"
flock -w 1800 8
[ -e "$OUT/recovery-required" ] || exit 0
failed() {
  status=$?; trap - ERR
  systemctl --user stop vllm-b12x-tailscale.service || true
  printf 'recovery failed rc=%s\n' "$status" > "$OUT/recovery-failed.txt" || true
  exit "$status"
}
trap failed ERR
systemctl --user stop vllm-b12x-tailscale.service
systemctl --user stop "b12x-$TASK-memory-a.service" "b12x-$TASK-memory-b.service" || true
systemctl --user stop vllm-b12x.service
# Fresh A, B and rollback can consume the unit's three-start budget. Reserve
# one bounded recovery reset; ExecStopPost retries never reset it again.
if [ ! -e "$OUT/recovery-reset-used" ]; then
  : > "$OUT/recovery-reset-used"
  systemctl --user reset-failed vllm-b12x.service
fi
printf '\n# --- %s rollback %s ---\n# Restore frozen control recipe/image and default allocator\nRECIPE=%s/%s\nIMAGE_TAG=%s\nB12X_ALLOCATOR_CONF=\n' "$TASK" "$(date -u +%FT%TZ)" "$ROOT" "$CONTROL_RECIPE" "$CONTROL_IMAGE_TAG" >> .env
systemctl --user start vllm-b12x.service
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
systemctl --user start vllm-b12x-watchdog.timer
systemctl --user is-active --quiet vllm-b12x.service
systemctl --user is-active --quiet vllm-b12x-watchdog.timer
systemctl --user start vllm-b12x-tailscale.service
for unit in vllm-b12x.service vllm-b12x-watchdog.timer vllm-b12x-tailscale.service; do
  systemctl --user is-active "$unit" >> "$OUT/rollback-units.txt"
done
mv "$OUT/recovery-required" "$OUT/recovery-complete"
date -u +%FT%TZ > "$OUT/recovery-success.txt"
