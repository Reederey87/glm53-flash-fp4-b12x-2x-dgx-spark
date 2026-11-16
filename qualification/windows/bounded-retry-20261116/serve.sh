#!/bin/bash
set -Eeuo pipefail
r=/home/nvidia/b12x-flare
w=$r/local/bounded-retry-window-20261116T050000Z
restore=b12x-flare-bounded-retry-restore-20261116T050000Z.service
trap 'systemctl --user start --no-block "$restore"' ERR
uv=/home/nvidia/.local/bin/uv
arm=$1
binary_sha=$2
[[ $arm =~ ^[0-9a-f]{64}$ && $binary_sha =~ ^[0-9a-f]{64}$ ]]
[[ $(sha256sum "$r/native/$arm/manifest.json" | cut -d ' ' -f1) == "$arm" ]]
[[ $(sha256sum "$r/native/$arm/flare" | cut -d ' ' -f1) == "$binary_sha" ]]
systemctl --user is-active --quiet b12x-flare-bounded-retry-restore-20261116T050000Z.timer
[[ -z $(docker ps -q --filter name=vllm_node) ]]
[[ -z $(ssh -n nvidia@192.168.177.11 docker ps -q --filter name=vllm_node) ]]
snap=/home/nvidia/.cache/huggingface/hub/models--nvidia--GLM-5.3-Flash-FP4-Local/snapshots/76348ddb2be2e35e39ecfc00e75dc07703f4f3d5
for policy in balanced latency; do
 ENV_FILE=/home/nvidia/b12x/.env "$r/scripts/wait_memory.sh" 600 </dev/null
 cat >> "$r/.env" <<ARM

# --- bounded policy comparison $policy 2026-11-16 UTC; docs/29 ---
# Frozen native/core/quant/KV/reserve; one scheduler policy variable.
FLARE_NATIVE_ARM=$arm
FLARE_SCHEDULER_POLICY=$policy
FLARE_SCHEDULER_TRACE=off
ARM
 ssh nvidia@192.168.177.11 'cat >> /home/nvidia/b12x-flare/.env' <<ARM

# --- bounded policy comparison $policy 2026-11-16 UTC; docs/29 ---
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
 systemd-run --user --unit="b12x-flare-bounded-retry-memory-$policy-20261116T050000Z" --property=Type=exec --property=RuntimeMaxSec=10000 "$uv" run --offline --no-project --python /usr/bin/python3 "$r/scripts/flare_memory_watch.py" --out "$w/$policy-memory.jsonl" --seconds 10000 --restore-unit "$restore"
 "$uv" run --offline --no-project --python /usr/bin/python3 "$w/verify-native.py" 0 "$policy" "$arm" "$binary_sha" > "$w/$policy-head-identity.json"
 ssh -n nvidia@192.168.177.11 "$uv run --offline --no-project --python /usr/bin/python3 $w/verify-native.py 1 $policy $arm $binary_sha" > "$w/$policy-worker-identity.json"
 systemctl --user show b12x-flare@0.service -p InvocationID --value > "$w/$policy-head-invocation.txt"
 ssh -n nvidia@192.168.177.11 systemctl --user show b12x-flare@1.service -p InvocationID --value > "$w/$policy-worker-invocation.txt"
 "$uv" run --offline --no-project --python "$r/upstream/flare/.venv/bin/python" "$r/scripts/flare_smoke.py" --base http://127.0.0.1:8001 --snapshot "$snap" --out "$w/$policy-smoke.json"
 "$uv" run --offline --no-project --python /usr/bin/python3 "$r/scripts/flare_mixed_bench.py" --base http://127.0.0.1:8001 --policy "$policy" --reps 3 --tokenizer "$snap/tokenizer.json" --run-id scheduler-latency-20261116 --out "$w/$policy-mixed.jsonl"
 printf '%s client_exit=0\n' "$policy" >> "$w/client-exits.txt"
 "$uv" run --offline --no-project --python /usr/bin/python3 - "$w/$policy-mixed.jsonl" <<'PY'
import json,sys
rows=[json.loads(x) for x in open(sys.argv[1])]
assert rows[-1]=={'complete':True,'cases':9,'requests':75}
assert len([x for x in rows if x.get('event')=='request'])==75
assert not any(x.get('event')=='request_error' for x in rows)
PY
 [[ "$policy" == balanced ]] || continue
 systemctl --user stop "b12x-flare-bounded-retry-memory-$policy-20261116T050000Z.service"
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
"$uv" run --offline --no-project --python /usr/bin/python3 "$r/scripts/flare_mixed_compare.py" --reference "$w/balanced-mixed.jsonl" --candidate "$w/latency-mixed.jsonl" --out "$w/mixed-comparison.json"
"$uv" run --offline --no-project --python /usr/bin/python3 python - "$w/mixed-comparison.json" <<'PYGATE'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]);d=json.loads(p.read_text())
bad=[r for r in d['points'] if r['observation']!='no_median_regression_over_2pct_observed']
print(json.dumps({'points':len(d['points']),'requires_investigation':bad}),flush=True)
assert not bad,'Mixed gate needs investigation; restore before further qualification'
p.with_name('mixed-gate-passed.txt').write_text('All registered mixed comparison points passed. Full matrix remains pending.\n')
PYGATE
