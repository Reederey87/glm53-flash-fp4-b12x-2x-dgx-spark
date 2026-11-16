#!/bin/bash
set -Eeuo pipefail
r=/home/nvidia/b12x-flare
w=$r/local/bounded-trace-window-20261116T060000Z
restore=b12x-flare-bounded-trace-restore-20261116T060000Z.service
trap 'systemctl --user start --no-block "$restore"' ERR
uv=/home/nvidia/.local/bin/uv
arm=127424e92c1e5845697d85f3c34ce93fa632dd48bf3be491c868c50a9deb0243
binary_sha=b2eb310b9ec9009fa499086777d9ed90105b323db70da527242286dc0de026b9
snap=/home/nvidia/.cache/huggingface/hub/models--nvidia--GLM-5.3-Flash-FP4-Local/snapshots/76348ddb2be2e35e39ecfc00e75dc07703f4f3d5
systemctl --user is-active --quiet b12x-flare-bounded-trace-restore-20261116T060000Z.timer
[[ $(sha256sum "$r/native/$arm/manifest.json" | cut -d ' ' -f1) == "$arm" ]]
[[ $(sha256sum "$r/native/$arm/flare" | cut -d ' ' -f1) == "$binary_sha" ]]
[[ $(sha256sum "$r/scripts/flare_run.py" | cut -d ' ' -f1) == 41b65a5a4bc39af18de9310d4096752809c223bea7ca4994cf8c2aa6f97e8793 ]]
ssh -n nvidia@192.168.177.11 "cd $r && sha256sum -c $w/runtime-source.sha256"
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
for policy in balanced latency; do
 ENV_FILE=/home/nvidia/b12x/.env "$r/scripts/wait_memory.sh" 600 </dev/null
 cat >> "$r/.env" <<ARM

# --- mixed diagnostic $policy 2026-11-16 UTC; docs/33 ---
# Frozen native/core/quant/KV/reserve; one scheduler policy variable.
FLARE_NATIVE_ARM=$arm
FLARE_SCHEDULER_POLICY=$policy
FLARE_SCHEDULER_TRACE=bounded-mixed-$policy-20261116t060000z.jsonl
ARM
 ssh nvidia@192.168.177.11 'cat >> /home/nvidia/b12x-flare/.env' <<ARM

# --- mixed diagnostic $policy 2026-11-16 UTC; docs/33 ---
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
 systemd-run --user --unit="b12x-flare-bounded-trace-memory-$policy-20261116T060000Z" --property=Type=exec --property=RuntimeMaxSec=900 "$uv" run --offline --no-project --python /usr/bin/python3 "$r/scripts/flare_memory_watch.py" --out "$w/$policy-memory.jsonl" --seconds 900 --restore-unit "$restore"
 "$uv" run --offline --no-project --python /usr/bin/python3 "$w/verify-native.py" 0 "$policy" "$arm" "$binary_sha" > "$w/$policy-head-identity.json"
 ssh -n nvidia@192.168.177.11 "$uv run --offline --no-project --python /usr/bin/python3 $w/verify-native.py 1 $policy $arm $binary_sha" > "$w/$policy-worker-identity.json"
 systemctl --user show b12x-flare@0.service -p InvocationID --value > "$w/$policy-head-invocation.txt"
 ssh -n nvidia@192.168.177.11 systemctl --user show b12x-flare@1.service -p InvocationID --value > "$w/$policy-worker-invocation.txt"
 "$uv" run --offline --no-project --python /usr/bin/python3 "$r/scripts/flare_mixed_bench.py" --base http://127.0.0.1:8001 --policy "$policy" --reps 1 --tokenizer "$snap/tokenizer.json" --run-id scheduler-latency-20261116 --out "$w/$policy-mixed.jsonl"
 printf '%s client_exit=0\n' "$policy" >> "$w/client-exits.txt"
 "$uv" run --offline --no-project --python /usr/bin/python3 - "$w/$policy-mixed.jsonl" <<'PY'
import json,sys
rows=[json.loads(x) for x in open(sys.argv[1])]
assert rows[-1]=={'complete':True,'cases':3,'requests':25}
assert len([x for x in rows if x.get('event')=='request'])==25
assert not any(x.get('event')=='request_error' for x in rows)
PY
 systemctl --user stop "b12x-flare-bounded-trace-memory-$policy-20261116T060000Z.service"
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
identity=json.loads((w/f'{policy}-head-identity.json').read_text())
p=Path(identity['trace_path']);raw=p.read_text();rows=[json.loads(x) for x in raw.splitlines()]
assert rows[0]['event']=='manifest'
end=rows[-1]
assert end['complete'] and not end['truncated'] and end['dropped_updates']==0,end
assert end['completions']==sum(x['event']=='completion' for x in rows),end
(w/f'{policy}-trace.jsonl').write_text(raw)
mem=[json.loads(x) for x in (w/f'{policy}-memory.jsonl').read_text().splitlines()]
assert mem and all(not x.get('violations') and not x.get('observation_error') for x in mem)
print(policy,'trace complete',end,'memory samples',len(mem),flush=True)
PY
done
systemctl --user start --no-block "$restore"
