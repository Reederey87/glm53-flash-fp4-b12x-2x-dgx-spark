#!/bin/bash
# Exact approved release activation; preparation/pins/fallback precede this.
set -Eeuo pipefail
r=/home/nvidia/b12x-flare
w=$r/local/production-adoption-20261116T113000Z/retry-20261116T114000Z
uv=/home/nvidia/.local/bin/uv
restore=b12x-flare-production-immediate-restore-20261116T113000Z.service
trap 'systemctl --user start --no-block "$restore"' ERR
[[ -f "$r/local/production-pending.json" ]]
systemctl --user is-active --quiet b12x-flare-production-rollback.timer
sha256sum --check "$w/source.sha256"
"$uv" run --offline --no-project --python /usr/bin/python3 "$r/scripts/flare_production.py" verify
ssh -n nvidia@192.168.177.11 "$uv" run --offline --no-project --python /usr/bin/python3 "$r/scripts/flare_production.py" verify --rank 1
image=sha256:3b5da79c42ed4204440cfb07c6de1eba46441d5cba6b57d5428d44e60c10d0ed
[[ $(docker inspect vllm_node --format '{{.Image}}') == "$image" ]]
[[ $(ssh -n nvidia@192.168.177.11 docker inspect vllm_node --format '{{.Image}}') == "$image" ]]
systemctl --user stop vllm-b12x-watchdog.timer vllm-b12x-tailscale.service
systemctl --user disable vllm-b12x-watchdog.timer vllm-b12x-tailscale.service vllm-b12x.service
systemctl --user stop vllm-b12x.service
[[ -z $(docker ps -q --filter name=vllm_node) ]]
[[ -z $(ssh -n nvidia@192.168.177.11 docker ps -q --filter name=vllm_node) ]]
ENV_FILE=/home/nvidia/b12x/.env "$r/scripts/wait_memory.sh" 600 </dev/null
systemd-run --user --unit=b12x-flare-production-memory-20261116T114000Z --property=Type=notify --property=NotifyAccess=all --property=TimeoutStartSec=30 --property=WatchdogSec=30 --property=LimitCORE=0 --property=OnFailure="$restore" --property=RuntimeMaxSec=5400 "$uv" run --offline --no-project --python /usr/bin/python3 "$r/scripts/flare_memory_watch.py" --out "$w/memory.jsonl" --seconds 5400 --restore-unit "$restore"
systemctl --user enable b12x-flare-production.service b12x-flare-production-watchdog.timer b12x-flare-tailscale.service
systemctl --user start b12x-flare-production.service
systemctl --user start b12x-flare-tailscale.service b12x-flare-production-watchdog.timer
for unit in b12x-flare-production.service b12x-flare-production-watchdog.timer b12x-flare-tailscale.service; do
 systemctl --user is-active --quiet "$unit"
 systemctl --user is-enabled --quiet "$unit"
done
curl --fail --silent --max-time 10 http://127.0.0.1:8001/health > "$w/activation-health.txt"
tailnet=$(tailscale ip -4 | head -1)
curl --fail --silent --max-time 10 "http://$tailnet:8000/health" > "$w/activation-tailnet-health.txt"
curl --fail --silent --max-time 10 http://127.0.0.1:8001/metrics > "$w/activation.metrics"
systemctl --user show b12x-flare-production.service b12x-flare@0.service -p Id -p InvocationID -p MainPID -p ActiveState -p ExecMainCode -p ExecMainStatus > "$w/activation-head.txt"
ssh -n nvidia@192.168.177.11 systemctl --user show b12x-flare@1.service -p Id -p InvocationID -p MainPID -p ActiveState > "$w/activation-worker.txt"
date -u > "$w/activation-complete.txt"
