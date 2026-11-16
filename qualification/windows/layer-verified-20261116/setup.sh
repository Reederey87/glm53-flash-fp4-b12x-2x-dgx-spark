#!/bin/bash
set -euo pipefail
r=/home/nvidia/b12x-flare
w=$r/local/layer-verified-window-20261116T180000Z
prior=$r/local/layer-matched-window-20261116T170000Z
[[ -f "$prior/restoration-verified.txt" && -f "$prior/fallback-disarmed.txt" ]]
[[ -f "$r/local/memory-notify-probe-20261116T140000Z/probe-passed.txt" ]]
mkdir "$w"
cp -n "$r/.env" "$w/head-env-before.private"
sha256sum "$r/.env" "$r/scripts/flare_run.py" "$r/local/accepted-core.json" > "$w/head-before.sha256"
docker inspect vllm_node --format '{{.Image}}' > "$w/head-image-before.txt"
ssh -n nvidia@192.168.177.11 "mkdir $w; cp -n $r/.env $w/worker-env-before.private; sha256sum $r/.env $r/scripts/flare_run.py $r/local/accepted-core.json > $w/worker-before.sha256; docker inspect vllm_node --format '{{.Image}}' > $w/worker-image-before.txt"
cat > "$w/restore.sh" <<'RESTORE'
#!/bin/bash
set -uo pipefail
for role in window rank0 memory; do
 systemctl --user stop "b12x-flare-layer-verified-$role-20261116T180000Z.service" || true
done
ssh -n -o BatchMode=yes -o ConnectTimeout=10 nvidia@192.168.177.11 systemctl --user stop b12x-flare-layer-verified-rank1-20261116T180000Z.service || true
exec /bin/bash /home/nvidia/b12x-flare/scripts/flare_restore.sh
RESTORE
systemd-run --user --unit=b12x-flare-layer-verified-restore-20261116T180000Z --on-active=90m --property=Type=exec --property=RemainAfterExit=yes /bin/bash "$w/restore.sh"
