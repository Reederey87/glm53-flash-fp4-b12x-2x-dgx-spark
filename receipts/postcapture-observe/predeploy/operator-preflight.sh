#!/usr/bin/env bash
set -euo pipefail
expected=sha256:3b5da79c42ed4204440cfb07c6de1eba46441d5cba6b57d5428d44e60c10d0ed
if [ "${1:-}" = --probe-image ]; then
  tmp=$(mktemp -d /tmp/b12x-postcapture-base.XXXXXX)
  c=$(docker create --entrypoint /bin/sh "$expected")
  cleanup() { docker rm "$c" >/dev/null; rm -f "$tmp/utils.py" "$tmp/model_runner.py" "$tmp/gpu_worker.py"; rmdir "$tmp"; }
  trap cleanup EXIT
  docker cp "$c:/usr/local/lib/python3.12/dist-packages/vllm/model_executor/model_loader/utils.py" "$tmp/utils.py"
  docker cp "$c:/usr/local/lib/python3.12/dist-packages/vllm/v1/worker/gpu/model_runner.py" "$tmp/model_runner.py"
  docker cp "$c:/usr/local/lib/python3.12/dist-packages/vllm/v1/worker/gpu_worker.py" "$tmp/gpu_worker.py"
  cd "$tmp"; sha256sum utils.py model_runner.py gpu_worker.py
  exit 0
fi
cd /home/nvidia/b12x
out=local/ab-postcapture-observe
stage=/home/nvidia/b12x-staging/postcapture-observe-3105eb5
self=/tmp/b12x-postcapture-observe-preflight-3105eb5.sh
test ! -e "$out/window.log"; test ! -e "$out/window-finished.txt"
sha256sum --check "$out/frozen.sha256"
test -z "$(docker ps -a --filter 'name=^/vllm_node$' --format '{{.ID}}')"
test -z "$(ssh -n nvidia@192.168.177.11 docker ps -a --filter 'name=^/vllm_node$' --format '{{.ID}}')"
[ "$(docker image inspect --format '{{.Id}}' vllm-node-b12x)" = "$expected" ]
[ "$(ssh -n nvidia@192.168.177.11 docker image inspect --format '{{.Id}}' vllm-node-b12x)" = "$expected" ]
ssh -n nvidia@192.168.177.11 "mkdir -p $stage/mods $stage/scripts"
rsync -a mods/startup-memory mods/startup-bound mods/startup-pinned mods/postcapture-heap nvidia@192.168.177.11:"$stage/mods/"
rsync -a scripts/check_postcapture_heap_cuda.py nvidia@192.168.177.11:"$stage/scripts/"
awk '$2 ~ /^mods\// || $2 == "scripts/check_postcapture_heap_cuda.py"' "$out/frozen.sha256" > "$out/worker-mods.sha256"
rsync -a "$out/worker-mods.sha256" nvidia@192.168.177.11:"$stage/frozen.sha256"
ssh -n nvidia@192.168.177.11 "cd $stage && sha256sum --check frozen.sha256" > "$out/worker-staged-verification.txt"
rsync -a "$self" nvidia@192.168.177.11:"$self"
bash "$self" --probe-image > "$out/head-base-sources.sha256"
ssh -n nvidia@192.168.177.11 bash "$self" --probe-image > "$out/worker-base-sources.sha256"
for node in head worker; do
 grep -qx 'aa398e74ee835537403e60186f2e9a81e8741a4b35fec68b47df6537716a45b7  utils.py' "$out/$node-base-sources.sha256"
 grep -qx 'aeadc5177c80789112c8e4836639b97e6fbb056711a4e6c81748c7ab9ad805d0  model_runner.py' "$out/$node-base-sources.sha256"
 grep -qx '668921c635ad810bfdb93a937ffa54a051859e5466cb8d941e1cb67e3e172e81  gpu_worker.py' "$out/$node-base-sources.sha256"
done
cp -n .env .env.bak-postcapture-observe-3105eb5
cmp .env .env.bak-postcapture-observe-3105eb5
sha256sum .env .env.bak-postcapture-observe-3105eb5 > "$out/env-before.sha256"
ssh -n nvidia@192.168.177.11 'test ! -e /home/nvidia/b12x/.env'
echo 'Worker has no b12x env; head owns append-only ledger' > "$out/worker-env-status.txt"
systemctl --user show b12x-recipe-window@postcapture-observe.service -p ExecStopPost -p KillMode > "$out/supervisor-before.txt"
grep -F 'recipe_recover.sh postcapture-observe' "$out/supervisor-before.txt"
grep -qx 'KillMode=mixed' "$out/supervisor-before.txt"
for unit in vllm-b12x-watchdog.timer vllm-b12x-watchdog.service vllm-b12x-tailscale.service; do [ "$(systemctl --user show "$unit" -p ActiveState --value)" = inactive ]; done
/home/nvidia/b12x/scripts/wait_memory.sh 30
test -z "$(docker ps -a --filter name=b12x-postcapture-probe --format '{{.ID}}')"
test -z "$(ssh -n nvidia@192.168.177.11 docker ps -a --filter name=b12x-postcapture-probe --format '{{.ID}}')"
echo 'All diagnostic preflights passed; no model start'
