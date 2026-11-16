#!/bin/bash
# Read-only identity/smoke receipt checks plus one public external API request.
set -euo pipefail
phase=${1:?activation, watchdog or reboot}
[[ $phase =~ ^(activation|watchdog|reboot)$ ]]
r=/home/nvidia/b12x-flare
w=$r/local/production-adoption-20261116T113000Z/retry-20261116T115000Z
uv=/home/nvidia/.local/bin/uv
for unit in b12x-flare-production.service b12x-flare-production-watchdog.timer b12x-flare-tailscale.service; do
 systemctl --user is-active --quiet "$unit"
 systemctl --user is-enabled --quiet "$unit"
done
for unit in vllm-b12x.service vllm-b12x-watchdog.timer vllm-b12x-tailscale.service; do
 ! systemctl --user is-active --quiet "$unit"
 ! systemctl --user is-enabled --quiet "$unit"
done
[[ -z $(docker ps -q --filter name=vllm_node) ]]
[[ -z $(ssh -n nvidia@192.168.177.11 docker ps -q --filter name=vllm_node) ]]
"$uv" run --offline --no-project --python /usr/bin/python3 "$r/scripts/flare_production.py" ready > "$w/$phase-ready.json"
owner=$(systemctl --user show b12x-flare-production.service -p InvocationID --value)
cp "$r/local/production-smoke-$owner.json" "$w/$phase-smoke.json"
"$uv" run --offline --no-project --python /usr/bin/python3 python - "$w/$phase-smoke.json" <<'PY'
import json,sys
from pathlib import Path
rows=json.loads(Path(sys.argv[1]).read_text())
assert len(rows)==7 and all(row['passed'] for row in rows),rows
PY
arm=127424e92c1e5845697d85f3c34ce93fa632dd48bf3be491c868c50a9deb0243
binary=b2eb310b9ec9009fa499086777d9ed90105b323db70da527242286dc0de026b9
"$uv" run --offline --no-project --python /usr/bin/python3 "$r/local/generation-window-20261117T060000Z/verify-native.py" 0 latency "$arm" "$binary" > "$w/$phase-head-identity.json"
ssh -n nvidia@192.168.177.11 "$uv" run --offline --no-project --python /usr/bin/python3 "$r/local/generation-window-20261117T060000Z/verify-native.py" 1 latency "$arm" "$binary" > "$w/$phase-worker-identity.json"
tailnet=$(tailscale ip -4 | head -1)
curl --fail --silent --show-error --max-time 5 --retry 60 --retry-delay 1 --retry-connrefused --retry-max-time 60 "http://$tailnet:8000/health" > "$w/$phase-tailnet-health.txt"
"$uv" run --offline --no-project --python /usr/bin/python3 python - "$tailnet" "$w/$phase-external-generation.json" <<'PY'
import json,sys,urllib.request
from pathlib import Path
body={'model':'nvidia/GLM-5.3-Flash-FP4-Local','messages':[{'role':'user','content':'Reply with the single word READY.'}],'max_tokens':256}
req=urllib.request.Request('http://'+sys.argv[1]+':8000/v1/chat/completions',json.dumps(body).encode(),{'Content-Type':'application/json'})
with urllib.request.urlopen(req,timeout=90) as response: result=json.load(response)
Path(sys.argv[2]).write_text(json.dumps({'request':body,'response':result},indent=2)+'\n')
assert result['usage']['completion_tokens']>0
assert 'READY' in result['choices'][0]['message'].get('content','').upper(),result
PY
systemctl --user show b12x-flare-production.service b12x-flare@0.service b12x-flare-production-watchdog.timer b12x-flare-tailscale.service -p Id -p ActiveState -p UnitFileState -p InvocationID -p MainPID -p ExecMainCode -p ExecMainStatus > "$w/$phase-head-units.txt"
ssh -n nvidia@192.168.177.11 systemctl --user show b12x-flare@1.service -p Id -p ActiveState -p InvocationID -p MainPID > "$w/$phase-worker-unit.txt"
cat /proc/sys/kernel/random/boot_id > "$w/$phase-head-boot.txt"
ssh -n nvidia@192.168.177.11 cat /proc/sys/kernel/random/boot_id > "$w/$phase-worker-boot.txt"
if [[ -f "$r/local/production-watchdog/state.json" ]]; then cp "$r/local/production-watchdog/state.json" "$w/$phase-watchdog-ledger.json"; fi
date -u +%FT%TZ > "$w/$phase-verified.txt"
