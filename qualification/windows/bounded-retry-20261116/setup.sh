set -euo pipefail
r=/home/nvidia/b12x-flare
w=$r/local/bounded-retry-window-20261116T050000Z
prior=$r/local/peer-drain-window-20261116T044500Z
[[ -f "$prior/lifecycle-gate-passed.txt" && -f "$prior/restoration-verified.txt" && -f "$prior/fallback-disarmed.txt" ]]
mkdir "$w"
cp -n "$r/.env" "$w/head-env-before.private"
sha256sum "$r/.env" "$r/scripts/flare_run.py" "$r/scripts/flare_lifecycle.py" > "$w/head-before.sha256"
docker inspect vllm_node --format '{{.Image}}' > "$w/head-image-before.txt"
systemctl --user is-enabled vllm-b12x.service vllm-b12x-watchdog.timer vllm-b12x-tailscale.service > "$w/head-units-before.txt"
ssh -n nvidia@192.168.177.11 "mkdir $w; cp -n $r/.env $w/worker-env-before.private; sha256sum $r/.env $r/scripts/flare_run.py $r/scripts/flare_lifecycle.py > $w/worker-before.sha256; docker inspect vllm_node --format '{{.Image}}' > $w/worker-image-before.txt"
cat > "$w/restore.sh" <<'RESTORE'
#!/bin/bash
set -uo pipefail
for role in serving-window memory-balanced memory-latency full-matrix loaded; do
 systemctl --user stop "b12x-flare-bounded-retry-$role-20261116T050000Z.service" || true
done
exec /bin/bash /home/nvidia/b12x-flare/scripts/flare_restore.sh
RESTORE
systemd-run --user --unit=b12x-flare-bounded-retry-restore-20261116T050000Z --on-active=180m --property=Type=exec --property=RemainAfterExit=yes /bin/bash "$w/restore.sh"
