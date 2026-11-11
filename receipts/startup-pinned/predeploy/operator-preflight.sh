#!/usr/bin/env bash
set -euo pipefail
expected=sha256:3b5da79c42ed4204440cfb07c6de1eba46441d5cba6b57d5428d44e60c10d0ed
if [ "${1:-}" = --probe-image ]; then
 tmp_probe=$(mktemp -d /tmp/b12x-bound-base.XXXXXX)
 probe=$(docker create --entrypoint /bin/sh "$expected")
 cleanup() { docker rm "$probe" >/dev/null; rm -f "$tmp_probe/utils.py"; rmdir "$tmp_probe"; }
 trap cleanup EXIT
 docker cp "$probe:/usr/local/lib/python3.12/dist-packages/vllm/model_executor/model_loader/utils.py" "$tmp_probe/utils.py"
 sha256sum "$tmp_probe/utils.py"
 exit 0
fi
cd /home/nvidia/b12x
out=local/ab-startup-pinned
stage=/home/nvidia/b12x-staging/startup-pinned-70075d3
test ! -e "$out/window.log"
test ! -e "$out/window-finished.txt"
test -f "$out/frozen.sha256"
sha256sum --check "$out/frozen.sha256"
test -z "$(docker ps -a --filter 'name=^/vllm_node$' --format '{{.ID}}')"
test -z "$(ssh -n nvidia@192.168.177.11 docker ps -a --filter 'name=^/vllm_node$' --format '{{.ID}}')"
[ "$(docker image inspect --format '{{.Id}}' vllm-node-b12x)" = "$expected" ]
[ "$(ssh -n nvidia@192.168.177.11 docker image inspect --format '{{.Id}}' vllm-node-b12x)" = "$expected" ]
ssh -n nvidia@192.168.177.11 "mkdir -p $stage/mods $stage/scripts"
rsync -a scripts/check_startup_bound_cuda.py scripts/check_pinned_cache_cuda.py nvidia@192.168.177.11:"$stage/scripts/"
rsync -a mods/startup-memory mods/startup-bound mods/startup-pinned nvidia@192.168.177.11:"$stage/mods/"
awk '$2 ~ /^mods\// || $2 == "scripts/check_startup_bound_cuda.py" || $2 == "scripts/check_pinned_cache_cuda.py"' "$out/frozen.sha256" > "$out/worker-mods.sha256"
rsync -a "$out/worker-mods.sha256" nvidia@192.168.177.11:"$stage/frozen.sha256"
ssh -n nvidia@192.168.177.11 "cd $stage && sha256sum --check frozen.sha256" > "$out/worker-staged-verification.txt"
rsync -a /tmp/b12x-startup-pinned-preflight-70075d3.sh nvidia@192.168.177.11:/tmp/b12x-startup-pinned-preflight-70075d3.sh
bash /tmp/b12x-startup-pinned-preflight-70075d3.sh --probe-image > "$out/head-base-loader.sha256"
ssh -n nvidia@192.168.177.11 bash /tmp/b12x-startup-pinned-preflight-70075d3.sh --probe-image > "$out/worker-base-loader.sha256"
for node in head worker; do read -r hash rest < "$out/$node-base-loader.sha256"; [ "$hash" = aa398e74ee835537403e60186f2e9a81e8741a4b35fec68b47df6537716a45b7 ]; done
cp -n .env .env.bak-startup-pinned-70075d3
cmp .env .env.bak-startup-pinned-70075d3
sha256sum .env .env.bak-startup-pinned-70075d3 > "$out/env-before.sha256"
ssh -n nvidia@192.168.177.11 'test ! -e /home/nvidia/b12x/.env'
echo 'Worker has no b12x env; head owns launch ledger' > "$out/worker-env-status.txt"
systemctl --user show b12x-recipe-window@startup-pinned.service -p ExecStopPost -p KillMode > "$out/supervisor-before.txt"
grep -F 'recipe_recover.sh startup-pinned' "$out/supervisor-before.txt"
grep -qx 'KillMode=mixed' "$out/supervisor-before.txt"
for unit in vllm-b12x-watchdog.timer vllm-b12x-watchdog.service vllm-b12x-tailscale.service; do [ "$(systemctl --user show "$unit" -p ActiveState --value)" = inactive ]; done
/home/nvidia/b12x/scripts/wait_memory.sh 30
test "$(/home/nvidia/.local/bin/uv run --offline python -c 'import sys; print(f"{int(sys.argv[1]):,}")' 2350210)" = 2,350,210
printf 'preflights complete; no server started\n'
