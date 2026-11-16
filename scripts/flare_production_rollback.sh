#!/usr/bin/env bash
# Used by the disk-installed calendar fallback during production/reboot gates.
set -euo pipefail
ROOT=/home/nvidia/b12x-flare
[[ $(hostname) == spark-a183 ]]
[[ -f "$ROOT/local/production-pending.json" ]] || exit 0
exec 8>"$ROOT/local/production-rollback.lock"
flock -n 8 || exit 0
# Revoke startup ownership before releasing memory or starting the incumbent.
systemctl --user disable --now b12x-flare-production-watchdog.timer
systemctl --user disable --now b12x-flare-tailscale.service
systemctl --user disable --now b12x-flare-production.service
/bin/bash "$ROOT/scripts/flare_production.sh" stop
cat >> "$ROOT/.env" <<'ARM'

# --- production qualification rollback; restore B12X ownership ---
FLARE_NATIVE_ARM=upstream
FLARE_SCHEDULER_POLICY=balanced
FLARE_SCHEDULER_TRACE=off
ARM
ssh -o BatchMode=yes -o ConnectTimeout=10 nvidia@192.168.177.11 \
    'cat >> /home/nvidia/b12x-flare/.env' <<'ARM'

# --- production qualification rollback; restore B12X ownership ---
FLARE_NATIVE_ARM=upstream
FLARE_SCHEDULER_POLICY=balanced
FLARE_SCHEDULER_TRACE=off
ARM
systemctl --user enable vllm-b12x.service vllm-b12x-watchdog.timer vllm-b12x-tailscale.service
/bin/bash "$ROOT/scripts/flare_restore.sh"
systemctl --user start vllm-b12x-watchdog.timer vllm-b12x-tailscale.service
printf '%s production fallback restored B12X; independent smoke still required\n' "$(date -u +%FT%TZ)"
# Keep the pending marker until an operator verifies both images and fresh smoke.
