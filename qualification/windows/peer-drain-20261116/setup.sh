set -euo pipefail
r=/home/nvidia/b12x-flare
w=$r/local/peer-drain-window-20261116T044500Z
mkdir "$w"
cp -n "$r/.env" "$w/head-env-before.private"
cp -n "$r/scripts/flare_run.py" "$w/head-flare_run.before.py"
sha256sum "$r/.env" "$r/scripts/flare_run.py" "$r/scripts/flare_lifecycle.py" > "$w/head-before.sha256"
docker inspect vllm_node --format '{{.Image}}' > "$w/head-image-before.txt"
systemctl --user is-enabled vllm-b12x.service vllm-b12x-watchdog.timer vllm-b12x-tailscale.service > "$w/head-units-before.txt"
ssh -n nvidia@192.168.177.11 "mkdir $w; cp -n $r/.env $w/worker-env-before.private; cp -n $r/scripts/flare_run.py $w/worker-flare_run.before.py; sha256sum $r/.env $r/scripts/flare_run.py $r/scripts/flare_lifecycle.py > $w/worker-before.sha256; docker inspect vllm_node --format '{{.Image}}' > $w/worker-image-before.txt"
cat > "$w/restore.sh" <<'RESTORE'
#!/bin/bash
set -uo pipefail
for role in orchestrate memory-graceful memory-peer-failure; do
 systemctl --user stop "b12x-flare-peer-drain-$role-20261116T044500Z.service" || true
done
exec /bin/bash /home/nvidia/b12x-flare/scripts/flare_restore.sh
RESTORE
systemd-run --user --unit=b12x-flare-peer-drain-restore-20261116T044500Z --on-active=60m --property=Type=exec --property=RemainAfterExit=yes /bin/bash "$w/restore.sh"
