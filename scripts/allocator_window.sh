#!/usr/bin/env bash
# Candidate 2 only; run through b12x-allocator-window.service.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
OUT="$ROOT/local/ab-20261110"
UV=/home/nvidia/.local/bin/uv
UNIT=vllm-b12x.service
EXPECTED=sha256:3b5da79c42ed4204440cfb07c6de1eba46441d5cba6b57d5428d44e60c10d0ed
GUARD=b12x-ab-memory-b.service
child=
finish() {
  primary=$?
  trap - EXIT
  # Further termination falls back to service ExecStopPost; do not make
  # recovery descendants inherit ignored signals and hold the recovery lock.
  trap - TERM INT
  if [ -n "$child" ]; then kill "$child" 2>/dev/null || true; wait "$child" 2>/dev/null || true; fi
  printf '%s\n' "$primary" > "$OUT/primary-status.txt"
  if /bin/bash "$ROOT/scripts/allocator_recover.sh"; then recovery=0; else recovery=$?; fi
  printf '%s\n' "$recovery" > "$OUT/recovery-status.txt"
  printf '%s primary=%s recovery=%s\n' "$(date -u +%FT%TZ)" "$primary" "$recovery" > "$OUT/window-finished.txt"
  [ "$primary" -eq 0 ] || exit "$primary"
  exit "$recovery"
}
trap finish EXIT
trap 'exit 143' TERM
trap 'exit 130' INT
guard_ok() {
  local stamp token invocation age
  local arm="${1:-b}"
  local unit="b12x-ab-memory-$arm.service"
  [ ! -e "$OUT/memory-$arm.csv.abort" ] || return 1
  systemctl --user is-active --quiet "$unit" || return 1
  read -r token stamp < "$OUT/memory-$arm.csv.ready" || return 1
  invocation=$(systemctl --user show "$unit" -p InvocationID --value) || return 1
  [ -n "$invocation" ] && [ "$token" = "$invocation" ] || return 1
  [[ "$stamp" =~ ^[0-9]+$ ]] || return 1
  age=$(( $(date +%s) - stamp ))
  [ "$age" -ge 0 ] && [ "$age" -le 20 ]
}
checked_run() {
  guard_ok || return 1
  "$@" & child=$!
  while kill -0 "$child" 2>/dev/null; do
    guard_ok || return 1
    sleep 2 & wait $!
  done
  local status=0
  wait "$child" || status=$?
  child=
  guard_ok || return 1
  return "$status"
}
# Missing, failed or transitional control jobs never authorize B.
deadline=$((SECONDS + 7200))
while true; do
  state=$(systemctl --user show b12x-ab-a.service -p ActiveState --value)
  case "$state" in
    active|activating|deactivating) [ "$SECONDS" -lt "$deadline" ] || exit 1; sleep 5 & wait $! ;;
    inactive) break ;;
    *) echo "control not successful: $state"; exit 1 ;;
  esac
done
[ "$(systemctl --user show b12x-ab-a.service -p Result --value)" = success ]
[ "$(systemctl --user show b12x-ab-a.service -p ExecMainStatus --value)" = 0 ]
[ ! -e "$OUT/memory-a.csv.abort" ]
systemctl --user is-active --quiet b12x-ab-memory-a.service
guard_ok a
"$UV" run --offline scripts/compare_matrix.py "$OUT/matrix-a.json" "$OUT/matrix-a.json" > "$OUT/control-validation.md"
grep -F '5/5 checks passed hard' "$OUT/control.log"
sha256sum --check "$OUT/candidate.sha256"
cmp recipes/glm-5.3-flash-fp4-local.yaml "$OUT/recipe.control.yaml"
systemctl --user stop vllm-b12x-watchdog.timer vllm-b12x-watchdog.service vllm-b12x-tailscale.service
for isolated in vllm-b12x-watchdog.timer vllm-b12x-watchdog.service vllm-b12x-tailscale.service; do
  [ "$(systemctl --user show "$isolated" -p ActiveState --value)" = inactive ]
done
docker logs vllm_node > "$OUT/control-server-final.log" 2>&1
# Durable marker lets ExecStopPost recover even after SIGKILL.
: > "$OUT/recovery-required"
systemctl --user stop b12x-ab-memory-a.service
systemctl --user stop "$UNIT"
printf '\n# --- allocator B %s ---\n# Independent variable: expandable segments, both ranks\n# Frozen: image/checkpoint, MTP3, 17G FP8 KV, four seats\n# Gate: docs/gates/2026-11-10-allocator.md\n# Rollback: B12X_ALLOCATOR_CONF=\nB12X_ALLOCATOR_CONF=expandable_segments:True\n' "$(date -u +%FT%TZ)" >> .env
systemd-run --user --unit=b12x-ab-memory-b /bin/bash "$ROOT/scripts/memory_guard.sh" "$OUT/memory-b.csv"
deadline=$((SECONDS + 30))
until guard_ok; do
  [ "$SECONDS" -lt "$deadline" ] || exit 1
  [ ! -e "$OUT/memory-b.csv.abort" ] || exit 1
  sleep 1 & wait $!
done
checked_run systemctl --user start "$UNIT"
for node in head worker; do
  if [ "$node" = head ]; then
    image=$(docker inspect --format '{{.Image}}' vllm_node)
    docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' vllm_node > "$OUT/head-b-env.txt"
    docker top vllm_node -eo pid,args > "$OUT/head-b-argv.txt"
  else
    image=$(ssh nvidia@192.168.177.11 docker inspect --format '{{.Image}}' vllm_node)
    ssh nvidia@192.168.177.11 "docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' vllm_node" > "$OUT/worker-b-env.txt"
    ssh nvidia@192.168.177.11 docker top vllm_node -eo pid,args > "$OUT/worker-b-argv.txt"
  fi
  [ "$image" = "$EXPECTED" ]
  grep -Fx 'PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True' "$OUT/$node-b-env.txt"
  if grep -q '^PYTORCH_ALLOC_CONF=' "$OUT/$node-b-env.txt"; then exit 1; fi
  guard_ok
done
docker logs vllm_node > "$OUT/candidate-boot.log" 2>&1
grep -F 'GPU KV cache size: 2,350,210 tokens' "$OUT/candidate-boot.log"
checked_run "$UV" run --offline scripts/smoke.py > "$OUT/smoke-b.txt" 2>&1
grep -F '5/5 checks passed hard' "$OUT/smoke-b.txt"
checked_run "$UV" run --offline scripts/speed_matrix.py --label allocator-b-probe --out "$OUT/probe-b.json" --lengths 8192 --concurrency 1 --reps 1
checked_run "$UV" run --offline scripts/speed_matrix.py --label allocator-b --out "$OUT/matrix-b.json"
cp -n "$OUT/matrix-b.json" "$OUT/matrix-b-initial.json"
checked_run "$UV" run --offline scripts/speed_matrix.py --label allocator-b-post --out "$OUT/matrix-b.json" --refresh-decode-from "$OUT/matrix-b-initial.json"
docker logs vllm_node > "$OUT/candidate-server-final.log" 2>&1
guard_ok
"$UV" run --offline scripts/compare_matrix.py "$OUT/matrix-a.json" "$OUT/matrix-b.json" > "$OUT/comparison.md" 2>&1
# EXIT and service ExecStopPost restore A; never auto-adopt.
