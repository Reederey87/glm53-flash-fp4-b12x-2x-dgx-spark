#!/usr/bin/env bash
# Idempotent EXIT/ExecStopPost recovery, serialized across both invocations.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
OUT="$ROOT/local/ab-20261110"
mkdir -p "$OUT"
exec 8>"$OUT/recovery.lock"
flock -w 1800 8
[ -e "$OUT/recovery-required" ] || exit 0
trap 'echo "recovery failed; external proxy remains stopped" > "$OUT/rollback-failed.txt"' ERR
systemctl --user stop vllm-b12x-tailscale.service
systemctl --user stop b12x-ab-memory-a.service b12x-ab-memory-b.service || true
systemctl --user stop vllm-b12x.service
printf '\n# --- allocator rollback %s ---\n# Restore tested image allocator default; IMAGE/recipe unchanged\nB12X_ALLOCATOR_CONF=\n' "$(date -u +%FT%TZ)" >> .env
systemctl --user start vllm-b12x.service
expected=sha256:3b5da79c42ed4204440cfb07c6de1eba46441d5cba6b57d5428d44e60c10d0ed
for node in head worker; do
  if [ "$node" = head ]; then
    image=$(docker inspect --format '{{.Image}}' vllm_node)
    docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' vllm_node > "$OUT/head-rollback-env.txt"
  else
    image=$(ssh nvidia@192.168.177.11 docker inspect --format '{{.Image}}' vllm_node)
    ssh nvidia@192.168.177.11 "docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' vllm_node" > "$OUT/worker-rollback-env.txt"
  fi
  [ "$image" = "$expected" ]
  # This pinned control image has neither variable; absence proves restoration.
  if grep -Eq '^PYTORCH_(CUDA_)?ALLOC_CONF=' "$OUT/$node-rollback-env.txt"; then exit 1; fi
done
/home/nvidia/.local/bin/uv run --offline scripts/smoke.py > "$OUT/rollback-smoke.txt" 2>&1
grep -F '5/5 checks passed hard' "$OUT/rollback-smoke.txt"
curl -fsS --max-time 10 http://127.0.0.1:8000/health > "$OUT/rollback-health.txt"
systemctl --user start vllm-b12x-watchdog.timer vllm-b12x-tailscale.service
systemctl --user is-active vllm-b12x.service vllm-b12x-watchdog.timer vllm-b12x-tailscale.service > "$OUT/rollback-units.txt"
mv "$OUT/recovery-required" "$OUT/recovery-complete"
date -u +%FT%TZ > "$OUT/recovery-success.txt"
