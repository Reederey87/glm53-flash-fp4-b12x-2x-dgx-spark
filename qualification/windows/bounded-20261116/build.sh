#!/bin/bash
set -Eeuo pipefail
r=/home/nvidia/b12x-flare
w=$r/local/bounded-window-20261116T041500Z
restore=b12x-flare-bounded-restore-20261116T041500Z.service
trap 'systemctl --user start --no-block "$restore"' ERR
uv=/home/nvidia/.local/bin/uv
snap=/home/nvidia/.cache/huggingface/hub/models--nvidia--GLM-5.3-Flash-FP4-Local/snapshots/76348ddb2be2e35e39ecfc00e75dc07703f4f3d5
systemctl --user is-active --quiet b12x-flare-bounded-restore-20261116T041500Z.timer
curl --fail --silent --max-time 10 http://127.0.0.1:8000/metrics > "$w/incumbent-before.metrics"
"$uv" run --offline --no-project --python /usr/bin/python3 - "$w/incumbent-before.metrics" <<'PY'
import sys
from pathlib import Path
rows=[x for x in Path(sys.argv[1]).read_text().splitlines() if x.startswith(('vllm:num_requests_running{','vllm:num_requests_waiting{'))]
assert len(rows)>=2 and all(float(x.rsplit(' ',1)[1])==0 for x in rows), rows
PY
systemctl --user stop vllm-b12x-watchdog.timer
systemctl --user stop vllm-b12x.service
[[ -z $(docker ps -q --filter name=vllm_node) ]]
[[ -z $(ssh -n nvidia@192.168.177.11 docker ps -q --filter name=vllm_node) ]]
ENV_FILE=/home/nvidia/b12x/.env "$r/scripts/wait_memory.sh" 600 </dev/null
build=b12x-flare-bounded-build-20261116T041500Z.service
lab=$r/local/bounded-scheduler-20261116T041500Z
commit=$1
ssh -n nvidia@192.168.177.11 "systemd-run --user --unit=$build --property=Type=exec --property=RemainAfterExit=yes --property=RuntimeMaxSec=2400 --property=TimeoutStopSec=60 --property=StandardOutput=append:$w/build.log --property=StandardError=append:$w/build.log /bin/bash $r/qualification/build_bounded_scheduler.sh $lab $commit"
for i in $(seq 1 480); do
 pid=$(ssh -n nvidia@192.168.177.11 systemctl --user show "$build" -p MainPID --value)
 [[ $pid != 0 ]] || break
 sleep 5
done
ssh -n nvidia@192.168.177.11 systemctl --user show "$build" -p Id -p MainPID -p ActiveState -p SubState -p ExecMainCode -p ExecMainStatus -p InvocationID > "$w/build-terminal.txt"
grep -qx 'MainPID=0' "$w/build-terminal.txt"
grep -qx 'ExecMainCode=1' "$w/build-terminal.txt"
grep -qx 'ExecMainStatus=0' "$w/build-terminal.txt"
scp -q "nvidia@192.168.177.11:$lab/artifact.json" "$w/artifact.json"
echo "Bounded candidate build completed; artifact retained for validation before staging."
