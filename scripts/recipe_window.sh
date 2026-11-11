#!/usr/bin/env bash
# Fresh A/B recipe window. Only systemd's template unit may run this driver.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TASK="${1:?window name required}"
[[ "$TASK" =~ ^[a-z0-9-]+$ ]] || exit 2
cd "$ROOT"
. "$ROOT/recipes/windows/$TASK.conf"
OUT="$ROOT/local/ab-$TASK"
UV=/home/nvidia/.local/bin/uv
mkdir -p "$OUT"
child=
loggers=()
stop_logs() {
  for pid in "${loggers[@]}"; do kill "$pid" 2>/dev/null || true; done
  for pid in "${loggers[@]}"; do wait "$pid" 2>/dev/null || true; done
  loggers=()
}
finish() {
  primary=$?; trap - EXIT; trap - TERM INT
  if [ -n "$child" ]; then kill "$child" 2>/dev/null || true; wait "$child" 2>/dev/null || true; fi
  stop_logs
  echo "$primary" > "$OUT/primary-status.txt"
  if /bin/bash scripts/recipe_recover.sh "$TASK"; then recovery=0; else recovery=$?; fi
  echo "$recovery" > "$OUT/recovery-status.txt"
  printf '%s primary=%s recovery=%s\n' "$(date -u +%FT%TZ)" "$primary" "$recovery" > "$OUT/window-finished.txt"
  [ "$primary" -eq 0 ] || exit "$primary"
  exit "$recovery"
}
trap finish EXIT
trap 'exit 143' TERM
trap 'exit 130' INT
run_plain() {
  "$@" & child=$!
  local status=0; wait "$child" || status=$?; child=
  return "$status"
}
guard_ok() {
  local token stamp invocation age
  [ ! -e "$OUT/memory-$arm.csv.abort" ] || return 1
  systemctl --user is-active --quiet "b12x-$TASK-memory-$arm.service" || return 1
  read -r token stamp < "$OUT/memory-$arm.csv.ready" || return 1
  invocation=$(systemctl --user show "b12x-$TASK-memory-$arm.service" -p InvocationID --value) || return 1
  [ -n "$invocation" ] && [ "$token" = "$invocation" ] || return 1
  [[ "$stamp" =~ ^[0-9]+$ ]] || return 1
  age=$(( $(date +%s) - stamp ))
  [ "$age" -ge 0 ] && [ "$age" -le 20 ]
}
capture_startup() {
  local node rank image
  for node in head worker; do
    [ ! -e "$OUT/$node-$arm.json" ] || continue
    if [ "$node" = head ]; then
      image=$(timeout 10 docker inspect --format '{{.Image}}' vllm_node 2>/dev/null) || continue
      rank=0
    else
      image=$(timeout 10 ssh -o ConnectTimeout=5 nvidia@192.168.177.11 docker inspect --format '{{.Image}}' vllm_node 2>/dev/null) || continue
      rank=1
    fi
    [ "$image" = "$expected_image" ] || return 1
    printf '%s\n' "$image" > "$OUT/$node-$arm.image"
    if [ ! -e "$OUT/$node-$arm.logging" ]; then
      if [ "$node" = head ]; then
        docker logs --follow vllm_node > "$OUT/$node-$arm-boot.log" 2>&1 &
      else
        ssh nvidia@192.168.177.11 docker logs --follow vllm_node > "$OUT/$node-$arm-boot.log" 2>&1 &
      fi
      loggers+=("$!"); : > "$OUT/$node-$arm.logging"
    fi
    if [ "$node" = head ]; then
      if ! timeout 15 docker exec -i vllm_node uv run --offline --no-project --python /usr/bin/python3 - < scripts/window_profile.py > "$OUT/$node-$arm.tmp" 2> "$OUT/$node-$arm-probe.err"; then continue; fi
    else
      if ! timeout 15 ssh -o ConnectTimeout=5 nvidia@192.168.177.11 docker exec -i vllm_node uv run --offline --no-project --python /usr/bin/python3 - < scripts/window_profile.py > "$OUT/$node-$arm.tmp" 2> "$OUT/$node-$arm-probe.err"; then continue; fi
    fi
    "$UV" run --offline scripts/window_profile.py --check "$OUT/$node-$arm.tmp" --backend "$backend" --seats "$seats" --rank "$rank" --kv "$KV_BYTES"
    mv "$OUT/$node-$arm.tmp" "$OUT/$node-$arm.json"
    printf '%s %s-%s profile verified\n' "$(date -u +%FT%TZ)" "$node" "$arm"
  done
}
checked_run() {
  guard_ok || return 1
  "$@" & child=$!
  while kill -0 "$child" 2>/dev/null; do
    guard_ok || return 1
    if [ "${booting:-0}" = 1 ]; then capture_startup; fi
    sleep 2 & wait $!
  done
  local status=0; wait "$child" || status=$?; child=
  guard_ok || return 1
  return "$status"
}

[ ! -e "$OUT/window-finished.txt" ] || { echo 'use a fresh window name/output directory'; exit 1; }
sha256sum --check "$OUT/frozen.sha256"
cp -n .env "$OUT/env.before"
sha256sum .env "$CONTROL_RECIPE" "$CANDIDATE_RECIPE" > "$OUT/before.sha256"
: > "$OUT/recovery-required"
run_plain systemctl --user stop vllm-b12x-watchdog.timer vllm-b12x-watchdog.service vllm-b12x-tailscale.service
for unit in vllm-b12x-watchdog.timer vllm-b12x-watchdog.service vllm-b12x-tailscale.service; do
  [ "$(systemctl --user show "$unit" -p ActiveState --value)" = inactive ]
done
# One explicit reset per reviewed window, never an unbounded heal loop.
systemctl --user reset-failed vllm-b12x.service
for arm in a b; do
  if [ "$arm" = a ]; then
    recipe="$CONTROL_RECIPE"; expected_image="$CONTROL_IMAGE_ID"; image_tag="$CONTROL_IMAGE_TAG"; backend="$CONTROL_BACKEND"; seats="$CONTROL_SEATS"
  else
    "$UV" run --offline scripts/compare_matrix.py "$OUT/matrix-a.json" "$OUT/matrix-a.json" > "$OUT/control-validation.md"
    recipe="$CANDIDATE_RECIPE"; expected_image="$CANDIDATE_IMAGE_ID"; image_tag="$CANDIDATE_IMAGE_TAG"; backend="$CANDIDATE_BACKEND"; seats="$CANDIDATE_SEATS"
    run_plain systemctl --user stop "b12x-$TASK-memory-a.service"
  fi
  run_plain systemctl --user stop vllm-b12x.service
  printf '\n# --- %s %s %s ---\n# Gate: docs/gates/%s.md; frozen controls in committed window config\n# Rollback: RECIPE=%s/%s IMAGE_TAG=%s B12X_ALLOCATOR_CONF=\nRECIPE=%s/%s\nIMAGE_TAG=%s\nB12X_ALLOCATOR_CONF=\n' "$TASK" "$arm" "$(date -u +%FT%TZ)" "$TASK" "$ROOT" "$CONTROL_RECIPE" "$CONTROL_IMAGE_TAG" "$ROOT" "$recipe" "$image_tag" >> .env
  systemd-run --user --unit="b12x-$TASK-memory-$arm" /bin/bash "$ROOT/scripts/memory_guard.sh" "$OUT/memory-$arm.csv"
  deadline=$((SECONDS + 30))
  until guard_ok; do
    [ "$SECONDS" -lt "$deadline" ] || exit 1
    [ ! -e "$OUT/memory-$arm.csv.abort" ] || exit 1
    sleep 1 & wait $!
  done
  booting=1
  checked_run systemctl --user start vllm-b12x.service
  capture_startup
  test -s "$OUT/head-$arm.json"; test -s "$OUT/worker-$arm.json"
  booting=0; stop_logs
  pool_formatted=$("$UV" run --offline -c 'import sys; print(f"{int(sys.argv[1]):,}")' "$KV_POOL")
  # The exact capacity is frozen in this first recipe window.
  grep -F "GPU KV cache size: $pool_formatted tokens" "$OUT/head-$arm-boot.log"
  checked_run "$UV" run --offline scripts/smoke.py > "$OUT/smoke-$arm.txt" 2>&1
  grep -F '5/5 checks passed hard' "$OUT/smoke-$arm.txt"
  checked_run "$UV" run --offline scripts/parity.py --label "$TASK-$arm" --out "$OUT"
  checked_run "$UV" run --offline scripts/speed_matrix.py --label "$TASK-$arm-probe" --out "$OUT/probe-$arm.json" --max-num-seqs "$seats" --lengths 8192 --concurrency 1 --reps 1
  checked_run "$UV" run --offline scripts/speed_matrix.py --label "$TASK-$arm" --out "$OUT/matrix-$arm-initial.json" --max-num-seqs "$seats"
  checked_run "$UV" run --offline scripts/speed_matrix.py --label "$TASK-$arm-post" --out "$OUT/matrix-$arm.json" --max-num-seqs "$seats" --refresh-decode-from "$OUT/matrix-$arm-initial.json"
  sha256sum "$OUT/matrix-$arm-initial.json" "$OUT/matrix-$arm.json" > "$OUT/matrix-$arm.sha256"
  docker logs vllm_node > "$OUT/head-$arm-final.log" 2>&1
done
"$UV" run --offline scripts/compare_matrix.py "$OUT/matrix-a.json" "$OUT/matrix-b.json" > "$OUT/comparison.md" 2>&1
# EXIT/ExecStopPost restore the frozen control even if every gate passes.
