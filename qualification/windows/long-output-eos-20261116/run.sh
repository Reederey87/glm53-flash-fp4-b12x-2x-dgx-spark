#!/bin/bash
set -Eeuo pipefail
r=/home/nvidia/b12x-flare
w=$r/local/long-output-eos-window-20261116T100000Z
restore=b12x-flare-long-output-eos-restore-20261116T100000Z.service
trap 'systemctl --user start --no-block "$restore"' ERR
uv=/home/nvidia/.local/bin/uv
arm=$1
binary_sha=$2
[[ $arm =~ ^[0-9a-f]{64}$ && $binary_sha =~ ^[0-9a-f]{64}$ ]]
[[ $(sha256sum "$r/native/$arm/manifest.json" | cut -d ' ' -f1) == "$arm" ]]
[[ $(sha256sum "$r/native/$arm/flare" | cut -d ' ' -f1) == "$binary_sha" ]]
systemctl --user is-active --quiet b12x-flare-long-output-eos-restore-20261116T100000Z.timer
[[ $(sha256sum "$r/scripts/flare_run.py" | cut -d ' ' -f1) == 41b65a5a4bc39af18de9310d4096752809c223bea7ca4994cf8c2aa6f97e8793 ]]
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
for policy in balanced latency; do
 ENV_FILE=/home/nvidia/b12x/.env "$r/scripts/wait_memory.sh" 600 </dev/null
 cat >> "$r/.env" <<ARM

# --- bounded policy comparison $policy 2026-11-16 UTC; docs/31,40 ---
# Frozen native/core/quant/KV/reserve; one scheduler policy variable.
FLARE_NATIVE_ARM=$arm
FLARE_SCHEDULER_POLICY=$policy
FLARE_SCHEDULER_TRACE=off
ARM
 ssh nvidia@192.168.177.11 'cat >> /home/nvidia/b12x-flare/.env' <<ARM

# --- bounded policy comparison $policy 2026-11-16 UTC; docs/31,40 ---
FLARE_NATIVE_ARM=$arm
FLARE_SCHEDULER_POLICY=$policy
FLARE_SCHEDULER_TRACE=off
ARM
 systemctl --user start b12x-flare@0.service
 ready=0
 for i in $(seq 1 240); do
   if curl --fail --silent --max-time 3 http://127.0.0.1:8001/health >/dev/null; then ready=1; break; fi
   systemctl --user is-active --quiet b12x-flare@0.service
   sleep 2
 done
 [[ $ready == 1 ]]
 systemd-run --user --unit="b12x-flare-long-output-eos-memory-$policy-20261116T100000Z" --property=Type=exec --property=RuntimeMaxSec=2700 "$uv" run --offline --no-project --python /usr/bin/python3 "$r/scripts/flare_memory_watch.py" --out "$w/$policy-memory.jsonl" --seconds 2700 --restore-unit "$restore"
 "$uv" run --offline --no-project --python /usr/bin/python3 "$w/verify-native.py" 0 "$policy" "$arm" "$binary_sha" > "$w/$policy-head-identity.json"
 ssh -n nvidia@192.168.177.11 "$uv run --offline --no-project --python /usr/bin/python3 $w/verify-native.py 1 $policy $arm $binary_sha" > "$w/$policy-worker-identity.json"
 curl --fail --silent --max-time 10 http://127.0.0.1:8001/metrics > "$w/$policy-start.metrics"
 "$uv" run --offline --no-project --python /usr/bin/python3 python - "$w/$policy-start.metrics" <<'PYCAP'
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
 systemctl --user show b12x-flare@0.service -p InvocationID --value > "$w/$policy-head-invocation.txt"
 ssh -n nvidia@192.168.177.11 systemctl --user show b12x-flare@1.service -p InvocationID --value > "$w/$policy-worker-invocation.txt"
 "$uv" run --offline --no-project --python "$r/upstream/flare/.venv/bin/python" "$r/scripts/flare_smoke.py" --base http://127.0.0.1:8001 --snapshot "$snap" --out "$w/$policy-smoke.json"
 "$uv" run --offline --no-project --python /usr/bin/python3 "$r/scripts/flare_long_output.py" run --base http://127.0.0.1:8001 --policy "$policy" --tokenizer "$snap/tokenizer.json" --run-id long-output-eos-20261116 --out "$w/$policy-long-output.jsonl"
 printf '%s client_exit=0\n' "$policy" >> "$w/client-exits.txt"
 "$uv" run --offline --no-project --python /usr/bin/python3 - "$w/$policy-long-output.jsonl" <<'PY'
import json,sys
rows=[json.loads(x) for x in open(sys.argv[1])]
assert rows[-1]=={'complete':True,'requests':12}
assert len([x for x in rows if 'rep' in x])==3
PY
 systemctl --user stop "b12x-flare-long-output-eos-memory-$policy-20261116T100000Z.service"
 systemctl --user stop b12x-flare@0.service
 inv=$(cat "$w/$policy-head-invocation.txt")
 cp "$r/local/native-exit-serve-rank0-$inv.json" "$w/$policy-head-exit.json"
 inv=$(cat "$w/$policy-worker-invocation.txt")
 scp -q "nvidia@192.168.177.11:$r/local/native-exit-serve-rank1-$inv.json" "$w/$policy-worker-exit.json"
 "$uv" run --offline --no-project --python /usr/bin/python3 - "$w" "$policy" <<'PY'
import json,sys
from pathlib import Path
w=Path(sys.argv[1]);policy=sys.argv[2]
for node in ('head','worker'):
 d=json.loads((w/f'{policy}-{node}-exit.json').read_text())
 assert d['native_returncode']==0 and not d['forced_kill'],d
 assert d['invocation_id']==(w/f'{policy}-{node}-invocation.txt').read_text().strip(),d
mem=[json.loads(x) for x in (w/f'{policy}-memory.jsonl').read_text().splitlines()]
assert mem and all(not x.get('violations') and not x.get('observation_error') for x in mem)
print(policy,'native exits passed; memory samples',len(mem),flush=True)
PY
done
"$uv" run --offline --no-project --python /usr/bin/python3 "$r/scripts/flare_long_output.py" compare --reference "$w/balanced-long-output.jsonl" --candidate "$w/latency-long-output.jsonl" --out "$w/comparison.json"
systemctl --user start --no-block "$restore"
