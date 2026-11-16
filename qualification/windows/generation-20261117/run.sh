#!/bin/bash
set -Eeuo pipefail
r=/home/nvidia/b12x-flare
w=$r/local/generation-window-20261117T060000Z
restore=b12x-flare-generation-restore-20261117T060000Z.service
trap 'systemctl --user start --no-block "$restore"' ERR
uv=/home/nvidia/.local/bin/uv
arm=127424e92c1e5845697d85f3c34ce93fa632dd48bf3be491c868c50a9deb0243
binary=b2eb310b9ec9009fa499086777d9ed90105b323db70da527242286dc0de026b9
image=sha256:3b5da79c42ed4204440cfb07c6de1eba46441d5cba6b57d5428d44e60c10d0ed
systemctl --user is-active --quiet b12x-flare-generation-restore-20261117T060000Z.timer
sha256sum --check "$w/head-source.sha256"
ssh -n nvidia@192.168.177.11 "cd $r && sha256sum --check $w/runtime-source.sha256"
[[ $(docker inspect vllm_node --format '{{.Image}}') == "$image" ]]
[[ $(ssh -n nvidia@192.168.177.11 docker inspect vllm_node --format '{{.Image}}') == "$image" ]]
curl --fail --silent --max-time 10 http://127.0.0.1:8000/metrics > "$w/incumbent-before.metrics"
"$uv" run --offline --no-project --python /usr/bin/python3 python - "$w/incumbent-before.metrics" <<'PY'
import sys
from pathlib import Path
rows=[x for x in Path(sys.argv[1]).read_text().splitlines() if x.startswith(('vllm:num_requests_running{','vllm:num_requests_waiting{'))]
assert len(rows)>=2 and all(float(x.rsplit(' ',1)[1])==0 for x in rows)
PY
systemctl --user stop vllm-b12x-watchdog.timer
timeout --signal=TERM --kill-after=30s 3600 "$uv" run --offline --no-project --python /usr/bin/python3 "$r/scripts/flare_generation.py" run --base http://127.0.0.1:8000 --engine vllm --run-id generation-20261117 --out "$w/reference.jsonl"
printf 'reference client_exit=0\n' >> "$w/client-exits.txt"
systemctl --user stop vllm-b12x.service
[[ -z $(docker ps -q --filter name=vllm_node) ]]
[[ -z $(ssh -n nvidia@192.168.177.11 docker ps -q --filter name=vllm_node) ]]
ENV_FILE=/home/nvidia/b12x/.env "$r/scripts/wait_memory.sh" 600 </dev/null
systemd-run --user --unit=b12x-flare-generation-memory-20261117T060000Z --property=Type=notify --property=NotifyAccess=all --property=TimeoutStartSec=30 --property=WatchdogSec=30 --property=LimitCORE=0 --property=OnFailure="$restore" --property=RuntimeMaxSec=8100 "$uv" run --offline --no-project --python /usr/bin/python3 "$r/scripts/flare_memory_watch.py" --out "$w/memory.jsonl" --seconds 8100 --restore-unit "$restore"
cat >> "$r/.env" <<ARM

# --- public generation comparison docs/53; 20261117T060000Z ---
# Frozen native/core/quant/KV/reserve4; semantic evidence, not a speed verdict.
FLARE_NATIVE_ARM=$arm
FLARE_SCHEDULER_POLICY=latency
FLARE_SCHEDULER_TRACE=off
ARM
ssh nvidia@192.168.177.11 'cat >> /home/nvidia/b12x-flare/.env' <<ARM

# --- public generation comparison docs/53; 20261117T060000Z ---
FLARE_NATIVE_ARM=$arm
FLARE_SCHEDULER_POLICY=latency
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
"$uv" run --offline --no-project --python /usr/bin/python3 "$w/verify-native.py" 0 latency "$arm" "$binary" > "$w/head-identity.json"
ssh -n nvidia@192.168.177.11 "$uv run --offline --no-project --python /usr/bin/python3 $w/verify-native.py 1 latency $arm $binary" > "$w/worker-identity.json"
systemctl --user show b12x-flare@0.service -p InvocationID --value > "$w/head-invocation.txt"
ssh -n nvidia@192.168.177.11 systemctl --user show b12x-flare@1.service -p InvocationID --value > "$w/worker-invocation.txt"
snap=/home/nvidia/.cache/huggingface/hub/models--nvidia--GLM-5.3-Flash-FP4-Local/snapshots/76348ddb2be2e35e39ecfc00e75dc07703f4f3d5
timeout --signal=TERM --kill-after=30s 300 "$uv" run --offline --no-project --python "$r/upstream/flare/.venv/bin/python" "$r/scripts/flare_smoke.py" --base http://127.0.0.1:8001 --snapshot "$snap" --out "$w/smoke.json"
timeout --signal=TERM --kill-after=30s 3600 "$uv" run --offline --no-project --python /usr/bin/python3 "$r/scripts/flare_generation.py" run --base http://127.0.0.1:8001 --engine flare --run-id generation-20261117 --out "$w/candidate.jsonl"
printf 'candidate client_exit=0\n' >> "$w/client-exits.txt"
systemctl --user stop b12x-flare@0.service
inv=$(cat "$w/head-invocation.txt")
cp "$r/local/native-exit-serve-rank0-$inv.json" "$w/head-exit.json"
inv=$(cat "$w/worker-invocation.txt")
scp -q "nvidia@192.168.177.11:$r/local/native-exit-serve-rank1-$inv.json" "$w/worker-exit.json"
"$uv" run --offline --no-project --python /usr/bin/python3 "$r/scripts/flare_generation.py" compare --reference "$w/reference.jsonl" --candidate "$w/candidate.jsonl" --out "$w/comparison.json"
"$uv" run --offline --no-project --python /usr/bin/python3 python - "$w" <<'PY'
import json,sys
from pathlib import Path
w=Path(sys.argv[1])
for node in ('head','worker'):
 d=json.loads((w/f'{node}-exit.json').read_text())
 assert d['native_returncode']==0 and not d['forced_kill'],d
 assert d['invocation_id']==(w/f'{node}-invocation.txt').read_text().strip(),d
mem=[json.loads(x) for x in (w/'memory.jsonl').read_text().splitlines()]
assert mem and all(not x.get('violations') and not x.get('observation_error') for x in mem)
assert json.loads((w/'comparison.json').read_text())['passed'] is True
PY
printf '%s Both engines passed all100 structural responses and50 semantic answers; no numerical equivalence claim.\n' "$(date -u +%FT%TZ)" > "$w/generation-gate-passed.txt"
systemctl --user stop b12x-flare-generation-memory-20261117T060000Z.service
systemctl --user start --no-block "$restore"
