#!/bin/bash
set -Eeuo pipefail
r=/home/nvidia/b12x-flare
w=$r/local/capacity-window-20261117T010000Z
restore=b12x-flare-capacity-restore-20261117T010000Z.service
trap 'systemctl --user start --no-block "$restore"' ERR
uv=/home/nvidia/.local/bin/uv
arm=$1
binary_sha=$2
[[ $arm =~ ^[0-9a-f]{64}$ && $binary_sha =~ ^[0-9a-f]{64}$ ]]
[[ $(sha256sum "$r/native/$arm/manifest.json" | cut -d ' ' -f1) == "$arm" ]]
[[ $(sha256sum "$r/native/$arm/flare" | cut -d ' ' -f1) == "$binary_sha" ]]
systemctl --user is-active --quiet b12x-flare-capacity-restore-20261117T010000Z.timer
[[ $(sha256sum "$r/scripts/flare_run.py" | cut -d ' ' -f1) == 8487477a39531194002fd429474c77ad1cffc37f2dab531ccf9b1dd1a8d509f3 ]]
ssh -n nvidia@192.168.177.11 "cd $r && sha256sum -c $w/runtime-source.sha256"
sha256sum --check "$w/head-source.sha256"
curl --fail --silent --max-time 10 http://127.0.0.1:8000/metrics > "$w/incumbent-before.metrics"
"$uv" run --offline --no-project --python /usr/bin/python3 python - "$w/incumbent-before.metrics" <<'PYIDLE'
import sys
from pathlib import Path
rows=[x for x in Path(sys.argv[1]).read_text().splitlines()
      if x.startswith(('vllm:num_requests_running{','vllm:num_requests_waiting{'))]
assert len(rows)>=2 and all(float(x.rsplit(' ',1)[1])==0 for x in rows)
PYIDLE
systemctl --user stop vllm-b12x-watchdog.timer
systemctl --user stop vllm-b12x.service
[[ -z $(docker ps -q --filter name=vllm_node) ]]
[[ -z $(ssh -n nvidia@192.168.177.11 docker ps -q --filter name=vllm_node) ]]
snap=/home/nvidia/.cache/huggingface/hub/models--nvidia--GLM-5.3-Flash-FP4-Local/snapshots/76348ddb2be2e35e39ecfc00e75dc07703f4f3d5
ENV_FILE=/home/nvidia/b12x/.env "$r/scripts/wait_memory.sh" 600 </dev/null
systemd-run --user --unit="b12x-flare-capacity-memory-20261117T010000Z" --property=Type=notify --property=NotifyAccess=all --property=TimeoutStartSec=30 --property=WatchdogSec=30 --property=LimitCORE=0 --property=OnFailure="$restore" --property=RuntimeMaxSec=5100 "$uv" run --offline --no-project --python /usr/bin/python3 "$r/scripts/flare_memory_watch.py" --out "$w/memory.jsonl" --seconds 5100 --restore-unit "$restore"
policy=latency
for reserve in 4 3.875; do
 label="reserve-$reserve"
 ENV_FILE=/home/nvidia/b12x/.env "$r/scripts/wait_memory.sh" 600 </dev/null
 cat >> "$r/.env" <<ARM

# --- capacity reserve $reserve $(date -u +%FT%TZ); docs/54 ---
# Frozen native/core/quant/policy; one explicit reserve variable.
FLARE_NATIVE_ARM=$arm
FLARE_SCHEDULER_POLICY=$policy
FLARE_SCHEDULER_TRACE=off
FLARE_SERVE_RESERVE_GIB=$reserve
ARM
 ssh nvidia@192.168.177.11 'cat >> /home/nvidia/b12x-flare/.env' <<ARM

# --- capacity reserve $reserve $(date -u +%FT%TZ); docs/54 ---
FLARE_NATIVE_ARM=$arm
FLARE_SCHEDULER_POLICY=$policy
FLARE_SCHEDULER_TRACE=off
FLARE_SERVE_RESERVE_GIB=$reserve
ARM
 systemctl --user start b12x-flare@0.service
 ready=0
 for i in $(seq 1 240); do
   if curl --fail --silent --max-time 3 http://127.0.0.1:8001/health >/dev/null; then ready=1; break; fi
   systemctl --user is-active --quiet b12x-flare@0.service
   sleep 2
 done
 [[ $ready == 1 ]]
 "$uv" run --offline --no-project --python /usr/bin/python3 "$w/verify-native.py" 0 "$policy" "$arm" "$binary_sha" "$reserve" > "$w/$label-head-identity.json"
 ssh -n nvidia@192.168.177.11 "$uv run --offline --no-project --python /usr/bin/python3 $w/verify-native.py 1 $policy $arm $binary_sha $reserve" > "$w/$label-worker-identity.json"
 curl --fail --silent --max-time 10 http://127.0.0.1:8001/metrics > "$w/$label-start.metrics"
 "$uv" run --offline --no-project --python /usr/bin/python3 python - "$w/$label-start.metrics" <<'PYCAP'
import json,sys
from pathlib import Path
raw=Path(sys.argv[1]).read_text()
names=('flare_total_kv_pages','flare_kv_page_tokens','flare_total_kv_tokens')
values={}
for name in names:
 rows=[r.split() for r in raw.splitlines() if r.startswith(name+' ')]
 assert len(rows)==1 and len(rows[0])==2
 values[name]=int(rows[0][1]);assert values[name]>0
assert values[names[0]]*values[names[1]]==values[names[2]]
print(json.dumps({'observed_startup_capacity':values,'capacity_adoption_gate_pending':True}),flush=True)
PYCAP
 systemctl --user show b12x-flare@0.service -p InvocationID --value > "$w/$label-head-invocation.txt"
 ssh -n nvidia@192.168.177.11 systemctl --user show b12x-flare@1.service -p InvocationID --value > "$w/$label-worker-invocation.txt"
 "$uv" run --offline --no-project --python "$r/upstream/flare/.venv/bin/python" "$r/scripts/flare_smoke.py" --base http://127.0.0.1:8001 --snapshot "$snap" --out "$w/$label-smoke.json"
 floor=()
 [[ $reserve != 3.875 ]] || floor=(--require-capacity-floor)
 timeout --signal=TERM --kill-after=30s 2400 "$uv" run --offline --no-project --python /usr/bin/python3 "$r/scripts/flare_capacity_stress.py" --base http://127.0.0.1:8001 --tokenizer "$snap/tokenizer.json" --run-id capacity-20261117 --out "$w/$label-stress.jsonl" "${floor[@]}"
 printf '%s client_exit=0\n' "$label" >> "$w/client-exits.txt"
 systemctl --user stop b12x-flare@0.service
 inv=$(cat "$w/$label-head-invocation.txt")
 cp "$r/local/native-exit-serve-rank0-$inv.json" "$w/$label-head-exit.json"
 inv=$(cat "$w/$label-worker-invocation.txt")
 scp -q "nvidia@192.168.177.11:$r/local/native-exit-serve-rank1-$inv.json" "$w/$label-worker-exit.json"
 "$uv" run --offline --no-project --python /usr/bin/python3 - "$w" "$label" <<'PY'
import json,sys
from pathlib import Path
w=Path(sys.argv[1]);policy=sys.argv[2]
for node in ('head','worker'):
 d=json.loads((w/f'{policy}-{node}-exit.json').read_text())
 assert d['native_returncode']==0 and not d['forced_kill'],d
 assert d['invocation_id']==(w/f'{policy}-{node}-invocation.txt').read_text().strip(),d
mem=[json.loads(x) for x in (w/'memory.jsonl').read_text().splitlines()]
assert mem and all(not x.get('violations') and not x.get('observation_error') for x in mem)
print(policy,'native exits passed; memory samples',len(mem),flush=True)
PY
done
"$uv" run --offline --no-project --python /usr/bin/python3 python - "$w" <<'PYGATE'
import json,sys
from pathlib import Path
w=Path(sys.argv[1]); rows={}
for reserve in ('4','3.875'):
 rows[reserve]=[json.loads(x) for x in (w/f'reserve-{reserve}-stress.jsonl').read_text().splitlines()]
 assert rows[reserve][-1]['complete'] is True
assert rows['4'][0]['manifest']['input_sha256']==rows['3.875'][0]['manifest']['input_sha256']
assert rows['3.875'][0]['manifest']['require_capacity_floor'] is True
assert (w/'client-exits.txt').read_text().splitlines()==['reserve-4 client_exit=0','reserve-3.875 client_exit=0']
PYGATE
printf '%s Candidate3.875GiB passed required capacity and concurrent-million-token streams; production adoption remains gated.\n' "$(date -u +%FT%TZ)" > "$w/capacity-gate-passed.txt"
# Keep one continuous notifying guard through every start/stop; stopping it queues restoration.
systemctl --user stop b12x-flare-capacity-memory-20261117T010000Z.service
systemctl --user start --no-block "$restore"
