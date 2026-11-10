#!/usr/bin/env bash
# Candidate 2 only. Queue after b12x-ab-a; always restore the control profile.
# Run as nvidia from the runtime tree via a separate systemd user service.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
OUT="$ROOT/local/ab-20261110"
UV=/home/nvidia/.local/bin/uv
UNIT=vllm-b12x.service
EXPECTED=sha256:3b5da79c42ed4204440cfb07c6de1eba46441d5cba6b57d5428d44e60c10d0ed
armed=0
cleanup() {
  rc=$?
  trap - EXIT
  if [ "$armed" = 1 ]; then
    systemctl --user stop b12x-ab-memory-a.service b12x-ab-memory-b.service || true
    systemctl --user stop "$UNIT" || true
    printf '\n# --- allocator rollback %s ---\n# Restore tested image allocator default; IMAGE and recipe unchanged\nB12X_ALLOCATOR_CONF=\n' "$(date -u +%FT%TZ)" >> .env
    if ! systemctl --user start "$UNIT"; then
      echo 'ROLLBACK START FAILED; inspect unit journal' > "$OUT/rollback-failed.txt"
      exit 1
    fi
    "$UV" run --offline scripts/smoke.py > "$OUT/rollback-smoke.txt" 2>&1 || rc=1
    curl -fsS --max-time 10 http://127.0.0.1:8000/health > "$OUT/rollback-health.txt" || rc=1
    systemctl --user start vllm-b12x-watchdog.timer vllm-b12x-tailscale.service || rc=1
    systemctl --user is-active "$UNIT" vllm-b12x-watchdog.timer vllm-b12x-tailscale.service > "$OUT/rollback-units.txt" || rc=1
  fi
  printf '%s exit=%s\n' "$(date -u +%FT%TZ)" "$rc" > "$OUT/window-finished.txt"
  exit "$rc"
}
trap cleanup EXIT

# Bound the wait. A full 3.8M-token control ladder can take over half an hour.
deadline=$((SECONDS + 7200))
while [ "$(systemctl --user show b12x-ab-a.service -p ActiveState --value)" = active ]; do
  [ "$SECONDS" -lt "$deadline" ] || { echo 'control wait timed out'; exit 1; }
  sleep 5
done
systemctl --user show b12x-ab-a.service -p Result -p ExecMainStatus > "$OUT/control-job-result.txt"
# Preserve failed controls as partial evidence; never turn them into a speed win.
docker logs vllm_node > "$OUT/control-server-final.log" 2>&1 || true
sha256sum --check "$OUT/candidate.sha256"
cmp recipes/glm-5.3-flash-fp4-local.yaml "$OUT/recipe.control.yaml"
armed=1
systemctl --user stop b12x-ab-memory-a.service || true
systemctl --user stop "$UNIT"
printf '\n# --- allocator B %s ---\n# Independent variable: expandable segments, both ranks\n# Frozen: pinned image/checkpoint, MTP3, 17G FP8 KV, four seats\n# Gate: local/ab-20261110/2026-11-10-allocator.md\n# Rollback: B12X_ALLOCATOR_CONF=\nB12X_ALLOCATOR_CONF=expandable_segments:True\n' "$(date -u +%FT%TZ)" >> .env
systemd-run --user --unit=b12x-ab-memory-b /bin/bash "$ROOT/scripts/memory_guard.sh" "$OUT/memory-b.csv"
systemctl --user start "$UNIT"
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
  [ "$image" = "$EXPECTED" ] || { echo "unexpected $node image: $image"; exit 1; }
  grep -Fx 'PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True' "$OUT/$node-b-env.txt"
done
"$UV" run --offline scripts/smoke.py | tee "$OUT/smoke-b.txt"
grep -F '5/5 checks passed hard' "$OUT/smoke-b.txt"
# Match the control's probe warmup before the measured full matrix.
"$UV" run --offline scripts/speed_matrix.py --label allocator-b-probe --out "$OUT/probe-b.json" --lengths 8192 --concurrency 1 --reps 1
"$UV" run --offline scripts/speed_matrix.py --label allocator-b --out "$OUT/matrix-b.json"
docker logs vllm_node > "$OUT/candidate-server-final.log" 2>&1
"$UV" run --offline scripts/compare_matrix.py "$OUT/matrix-a.json" "$OUT/matrix-b.json" > "$OUT/comparison.md" || true
# EXIT trap restores A even when the candidate passes. Approval follows receipts.
