#!/bin/bash
set -Eeuo pipefail
r=/home/nvidia/b12x-flare
w=$r/local/layer-repeatability-window-20261116T110000Z
restore=b12x-flare-layer-repeatability-restore-20261116T110000Z.service
trap 'systemctl --user start --no-block "$restore"' ERR
uv=/home/nvidia/.local/bin/uv
systemctl --user is-active --quiet b12x-flare-layer-repeatability-restore-20261116T110000Z.timer
sha256sum --check "$w/runtime-source.sha256"
ssh -n nvidia@192.168.177.11 "sha256sum --check $w/runtime-source.sha256"
curl --fail --silent --max-time 10 http://127.0.0.1:8000/metrics > "$w/incumbent-before.metrics"
"$uv" run --offline --no-project --python /usr/bin/python3 python - "$w/incumbent-before.metrics" <<'PY'
import sys
from pathlib import Path
rows=[x for x in Path(sys.argv[1]).read_text().splitlines() if x.startswith(('vllm:num_requests_running{','vllm:num_requests_waiting{'))]
assert len(rows)>=2 and all(float(x.rsplit(' ',1)[1])==0 for x in rows)
PY
systemctl --user stop vllm-b12x-watchdog.timer vllm-b12x.service
[[ -z $(docker ps -q --filter name=vllm_node) ]]
[[ -z $(ssh -n nvidia@192.168.177.11 docker ps -q --filter name=vllm_node) ]]
ENV_FILE=/home/nvidia/b12x/.env "$r/scripts/wait_memory.sh" 600 </dev/null
systemd-run --user --unit=b12x-flare-layer-repeatability-memory-20261116T110000Z --property=Type=exec --property=RuntimeMaxSec=4800 "$uv" run --offline --no-project --python /usr/bin/python3 "$r/scripts/flare_memory_watch.py" --out "$w/memory.jsonl" --seconds 4800 --restore-unit "$restore"
ssh -n nvidia@192.168.177.11 "systemd-run --user --unit=b12x-flare-layer-repeatability-rank1-20261116T110000Z --property=Type=exec --property=RemainAfterExit=yes --property=RuntimeMaxSec=3900 --property=StandardOutput=append:$w/rank1.log --property=StandardError=append:$w/rank1.log /bin/bash $r/qualification/run_layer_repeatability.sh 1 $w/rank1"
systemd-run --user --unit=b12x-flare-layer-repeatability-rank0-20261116T110000Z --property=Type=exec --property=RemainAfterExit=yes --property=RuntimeMaxSec=3900 --property=StandardOutput=append:"$w/rank0.log" --property=StandardError=append:"$w/rank0.log" /bin/bash "$r/qualification/run_layer_repeatability.sh" 0 "$w/rank0"
end=$((SECONDS+4200))
while :; do
 [[ $SECONDS -lt $end ]]
 head_pid=$(systemctl --user show b12x-flare-layer-repeatability-rank0-20261116T110000Z.service -p MainPID --value)
 worker_pid=$(ssh -n -o ConnectTimeout=10 nvidia@192.168.177.11 systemctl --user show b12x-flare-layer-repeatability-rank1-20261116T110000Z.service -p MainPID --value)
 if [[ $head_pid == 0 ]]; then
  [[ $(systemctl --user show b12x-flare-layer-repeatability-rank0-20261116T110000Z.service -p ExecMainCode --value) == 1 ]]
  [[ $(systemctl --user show b12x-flare-layer-repeatability-rank0-20261116T110000Z.service -p ExecMainStatus --value) =~ ^[01]$ ]]
 fi
 if [[ $worker_pid == 0 ]]; then
  [[ $(ssh -n nvidia@192.168.177.11 systemctl --user show b12x-flare-layer-repeatability-rank1-20261116T110000Z.service -p ExecMainCode --value) == 1 ]]
  [[ $(ssh -n nvidia@192.168.177.11 systemctl --user show b12x-flare-layer-repeatability-rank1-20261116T110000Z.service -p ExecMainStatus --value) =~ ^[01]$ ]]
 fi
 [[ $head_pid != 0 || $worker_pid != 0 ]] || break
 sleep 5
done
systemctl --user show b12x-flare-layer-repeatability-rank0-20261116T110000Z.service -p Id -p InvocationID -p MainPID -p ExecMainCode -p ExecMainStatus > "$w/rank0-terminal.txt"
ssh -n nvidia@192.168.177.11 systemctl --user show b12x-flare-layer-repeatability-rank1-20261116T110000Z.service -p Id -p InvocationID -p MainPID -p ExecMainCode -p ExecMainStatus > "$w/rank1-terminal.txt"
scp -q "nvidia@192.168.177.11:$w/rank1/summary.json" "$w/rank1-summary.json"
"$uv" run --offline --no-project --python /usr/bin/python3 python - "$w" <<'PY'
import json,sys
from pathlib import Path
w=Path(sys.argv[1])
for p in (w/'rank0/summary.json',w/'rank1-summary.json'):
 d=json.loads(p.read_text());assert d['diagnostic_complete'] and d['cases']==1,d
mem=[json.loads(x) for x in (w/'memory.jsonl').read_text().splitlines()]
assert mem and all(not x.get('violations') and not x.get('observation_error') for x in mem)
PY
sha256sum --check "$w/head-before.sha256" > "$w/unchanged-runtime-after.txt"
ssh -n nvidia@192.168.177.11 "sha256sum --check $w/worker-before.sha256" >> "$w/unchanged-runtime-after.txt"
printf '%s Both ranks completed six matched-state repeatability observations; original numerical failures remain authoritative.\n' "$(date -u +%FT%TZ)" > "$w/diagnostic-complete.txt"
systemctl --user stop b12x-flare-layer-repeatability-memory-20261116T110000Z.service
systemctl --user start --no-block "$restore"
