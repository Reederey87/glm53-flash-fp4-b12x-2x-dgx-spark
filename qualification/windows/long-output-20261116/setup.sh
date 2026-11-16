set -euo pipefail
r=/home/nvidia/b12x-flare
w=$r/local/long-output-window-20261116T080000Z
prior=$r/local/native-mla-window-20261116T070000Z
[[ -f "$prior/restoration-verified.txt" && -f "$prior/fallback-disarmed.txt" && -f "$prior/mla-gate-passed.txt" ]]
mkdir "$w"
cp -n "$r/.env" "$w/head-env-before.private"
sha256sum "$r/.env" "$r/scripts/flare_run.py" "$r/scripts/flare_lifecycle.py" "$r/local/accepted-core.json" > "$w/head-before.sha256"
docker inspect vllm_node --format '{{.Image}}' > "$w/head-image-before.txt"
systemctl --user is-enabled vllm-b12x.service vllm-b12x-watchdog.timer vllm-b12x-tailscale.service > "$w/head-units-before.txt"
ssh -n nvidia@192.168.177.11 "mkdir $w; cp -n $r/.env $w/worker-env-before.private; sha256sum $r/.env $r/scripts/flare_run.py $r/scripts/flare_lifecycle.py $r/local/accepted-core.json > $w/worker-before.sha256; docker inspect vllm_node --format '{{.Image}}' > $w/worker-image-before.txt"
cat > "$w/restore.sh" <<'RESTORE'
#!/bin/bash
set -uo pipefail
for role in orchestrate memory-balanced memory-latency; do
 systemctl --user stop "b12x-flare-long-output-$role-20261116T080000Z.service" || true
done
exec /bin/bash /home/nvidia/b12x-flare/scripts/flare_restore.sh
RESTORE
systemd-run --user --unit=b12x-flare-long-output-restore-20261116T080000Z --on-active=60m --property=Type=exec --property=RemainAfterExit=yes /bin/bash "$w/restore.sh"
