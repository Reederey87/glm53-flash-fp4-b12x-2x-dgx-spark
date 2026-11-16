#!/bin/bash
set -Eeuo pipefail
r=/home/nvidia/b12x-flare
w=$r/local/peer-drain-window-20261116T044500Z
restore=b12x-flare-peer-drain-restore-20261116T044500Z.service
trap 'systemctl --user start --no-block "$restore"' ERR
uv=/home/nvidia/.local/bin/uv
arm=127424e92c1e5845697d85f3c34ce93fa632dd48bf3be491c868c50a9deb0243
binary=b2eb310b9ec9009fa499086777d9ed90105b323db70da527242286dc0de026b9
snap=/home/nvidia/.cache/huggingface/hub/models--nvidia--GLM-5.3-Flash-FP4-Local/snapshots/76348ddb2be2e35e39ecfc00e75dc07703f4f3d5
systemctl --user is-active --quiet b12x-flare-peer-drain-restore-20261116T044500Z.timer
# The staged source must match the committed wrapper selected before the window.
"$uv" run --offline --no-project --python /usr/bin/python3 python - "$w/runtime-source.json" "$r/scripts/flare_run.py" <<'PY'
import hashlib,json,sys
from pathlib import Path
m=json.loads(Path(sys.argv[1]).read_text())
assert hashlib.sha256(Path(sys.argv[2]).read_bytes()).hexdigest()==m['sha256']
print(json.dumps(m),flush=True)
PY
ssh -n nvidia@192.168.177.11 "cd $r && sha256sum -c $w/runtime-source.sha256"
curl --fail --silent --max-time 10 http://127.0.0.1:8000/metrics > "$w/incumbent-before.metrics"
"$uv" run --offline --no-project --python /usr/bin/python3 python - "$w/incumbent-before.metrics" <<'PY'
import sys
from pathlib import Path
rows=[x for x in Path(sys.argv[1]).read_text().splitlines() if x.startswith(('vllm:num_requests_running{','vllm:num_requests_waiting{'))]
assert len(rows)>=2 and all(float(x.rsplit(' ',1)[1])==0 for x in rows)
PY
systemctl --user stop vllm-b12x-watchdog.timer
systemctl --user stop vllm-b12x.service
[[ -z $(docker ps -q --filter name=vllm_node) ]]
[[ -z $(ssh -n nvidia@192.168.177.11 docker ps -q --filter name=vllm_node) ]]
cat >> "$r/.env" <<ARM

# --- peer drain qualification 2026-11-16 UTC; docs/28 ---
# Only wrapper shutdown ordering changes; native/core and balanced policy frozen.
FLARE_NATIVE_ARM=$arm
FLARE_SCHEDULER_POLICY=balanced
FLARE_SCHEDULER_TRACE=off
ARM
ssh nvidia@192.168.177.11 'cat >> /home/nvidia/b12x-flare/.env' <<ARM

# --- peer drain qualification 2026-11-16 UTC; docs/28 ---
FLARE_NATIVE_ARM=$arm
FLARE_SCHEDULER_POLICY=balanced
FLARE_SCHEDULER_TRACE=off
ARM
for action in graceful peer-failure; do
 "$uv" run --offline --no-project --python /usr/bin/python3 "$r/scripts/flare_release_file_cache.py"
 ssh -n nvidia@192.168.177.11 "$uv" run --offline --no-project --python /usr/bin/python3 "$r/scripts/flare_release_file_cache.py"
 ENV_FILE=/home/nvidia/b12x/.env "$r/scripts/wait_memory.sh" 600 </dev/null
 systemctl --user start b12x-flare@0.service
 ready=0
 for i in $(seq 1 240); do
  if curl --fail --silent --max-time 3 http://127.0.0.1:8001/health >/dev/null; then ready=1; break; fi
  systemctl --user is-active --quiet b12x-flare@0.service
  sleep 2
 done
 [[ $ready == 1 ]]
 systemd-run --user --unit="b12x-flare-peer-drain-memory-$action-20261116T044500Z" --property=Type=exec --property=RuntimeMaxSec=900 "$uv" run --offline --no-project --python /usr/bin/python3 "$r/scripts/flare_memory_watch.py" --out "$w/$action-memory.jsonl" --seconds 900 --restore-unit "$restore"
 "$uv" run --offline --no-project --python /usr/bin/python3 "$w/verify-native.py" 0 balanced "$arm" "$binary" > "$w/$action-head-identity.json"
 ssh -n nvidia@192.168.177.11 "$uv" run --offline --no-project --python /usr/bin/python3 "$w/verify-native.py" 1 balanced "$arm" "$binary" > "$w/$action-worker-identity.json"
 "$uv" run --offline --no-project --python "$r/upstream/flare/.venv/bin/python" "$r/scripts/flare_smoke.py" --base http://127.0.0.1:8001 --snapshot "$snap" --out "$w/$action-smoke.json"
 systemctl --user stop "b12x-flare-peer-drain-memory-$action-20261116T044500Z.service"
 "$uv" run --offline --no-project --python /usr/bin/python3 python - "$w/$action-memory.jsonl" <<'PY'
import json,sys
rows=[json.loads(x) for x in open(sys.argv[1])]
assert rows and all(not r.get('violations') and not r.get('observation_error') for r in rows)
print('Serving memory samples passed:',len(rows),flush=True)
PY
 "$uv" run --offline --no-project --python /usr/bin/python3 "$r/scripts/flare_lifecycle.py" --action "$action" --out "$w/$action-lifecycle.jsonl" --restore-timer b12x-flare-peer-drain-restore-20261116T044500Z.timer
 printf '%s client_exit=0\n' "$action" >> "$w/client-exits.txt"
 tail -25 "$r/logs/serve-rank0.log" > "$w/$action-head-shutdown.log"
 "$uv" run --offline --no-project --python /usr/bin/python3 python - "$w/$action-lifecycle.jsonl" <<'PY'
import json,sys
rows=[json.loads(x) for x in open(sys.argv[1])]
assert rows[-1]['event']=='passed' and rows[-1]['operation_locks_released']
print(json.dumps(rows[-1]),flush=True)
PY
done
printf 'Both loaded lifecycle cases passed; production adoption remains gated.\n' > "$w/lifecycle-gate-passed.txt"
systemctl --user start --no-block "$restore"
