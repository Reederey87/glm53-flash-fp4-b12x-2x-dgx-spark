#!/bin/bash
set -euo pipefail
r=/home/nvidia/b12x-flare
w=$r/local/production-adoption-20261116T113000Z/retry-20261116T120500Z
[[ -f "$w/watchdog-recovery-complete.txt" ]]
for u in b12x-flare-production.service b12x-flare-production-watchdog.timer b12x-flare-tailscale.service; do
 systemctl --user is-active --quiet "$u"
 systemctl --user is-enabled --quiet "$u"
done
systemctl --user is-active --quiet b12x-flare-production-rollback.timer
cat /proc/sys/kernel/random/boot_id > "$w/reboot-head-before.txt"
uname -r > "$w/reboot-head-kernel-before.txt"
nvidia-smi --query-gpu=driver_version --format=csv,noheader > "$w/reboot-head-driver-before.txt"
ssh -n nvidia@192.168.177.11 cat /proc/sys/kernel/random/boot_id > "$w/reboot-worker-before.txt"
ssh -n nvidia@192.168.177.11 uname -r > "$w/reboot-worker-kernel-before.txt"
ssh -n nvidia@192.168.177.11 nvidia-smi --query-gpu=driver_version --format=csv,noheader > "$w/reboot-worker-driver-before.txt"
# Disable this window's failure callback before deliberately stopping its guard.
touch "$r/local/production-guard-disarmed"
systemctl --user stop b12x-flare-production-watchdog.timer
systemctl --user stop b12x-flare-production-memory-20261116T120500Z.service
systemctl --user stop b12x-flare-production.service
! systemctl --user is-active --quiet b12x-flare@0.service
! ssh -n nvidia@192.168.177.11 systemctl --user is-active --quiet b12x-flare@1.service
[[ -z $(docker ps -q --filter name=vllm_node) ]]
[[ -z $(ssh -n nvidia@192.168.177.11 docker ps -q --filter name=vllm_node) ]]
systemctl --user list-timers b12x-flare-production-rollback.timer --no-pager > "$w/reboot-fallback-armed.txt"
date -u +%FT%TZ > "$w/reboot-stopped-safely.txt"
