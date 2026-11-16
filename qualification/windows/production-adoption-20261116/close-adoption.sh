#!/bin/bash
set -euo pipefail
r=/home/nvidia/b12x-flare
w=$r/local/production-adoption-20261116T113000Z/retry-20261116T120500Z
[[ -f "$w/reboot-verification-complete.txt" ]]
u=b12x-flare-production-reboot-check-20261116T120500Z.service
[[ $(systemctl --user show "$u" -p MainPID --value) == 0 ]]
[[ $(systemctl --user show "$u" -p ExecMainCode --value) == 1 ]]
[[ $(systemctl --user show "$u" -p ExecMainStatus --value) == 0 ]]
systemctl --user show "$u" -p Id -p InvocationID -p MainPID -p ExecMainCode -p ExecMainStatus > "$w/reboot-check-outcome.txt"
for unit in b12x-flare-production.service b12x-flare-production-watchdog.timer b12x-flare-tailscale.service; do
 systemctl --user is-active --quiet "$unit"
 systemctl --user is-enabled --quiet "$unit"
done
systemctl --user is-active --quiet b12x-flare@0.service
ssh -n nvidia@192.168.177.11 systemctl --user is-active --quiet b12x-flare@1.service
curl --fail --silent --max-time 10 http://127.0.0.1:8001/health >/dev/null
touch "$r/local/production-guard-disarmed"
systemctl --user stop b12x-flare-production-boot-memory-20261116T120500Z.service
/home/nvidia/.local/bin/uv run --offline --no-project --python /usr/bin/python3 python - "$w" <<'PY'
import json,sys
from pathlib import Path
w=Path(sys.argv[1]); report={}
for name in ('memory.jsonl','reboot-memory.jsonl'):
 rows=[json.loads(line) for line in (w/name).read_text().splitlines()]
 assert rows and all(not row.get('violations') and not row.get('observation_error') for row in rows)
 report[name]={'samples':len(rows),'start':rows[0]['time'],'end':rows[-1]['time'],'minimum_gib':{node:{metric:min(row['nodes'][node][metric] for row in rows)/(1<<30) for metric in ('MemFree','MemAvailable')} for node in ('head','worker')}}
(w/'final-memory-summary.json').write_text(json.dumps(report,indent=2)+'\n')
PY
mv "$r/local/production-pending.json" "$w/production-pending-closed.json"
systemctl --user disable --now b12x-flare-production-rollback.timer
systemctl --user stop "$u"
! systemctl --user is-active --quiet b12x-flare-production-rollback.timer
! systemctl --user is-enabled --quiet b12x-flare-production-rollback.timer
[[ ! -e "$r/local/production-pending.json" ]]
systemctl --user show b12x-flare-production-rollback.timer -p ActiveState -p UnitFileState > "$w/fallback-closed.txt"
cat "$r/local/production-watchdog/state.json" > "$w/final-watchdog-ledger.json"
systemctl --user is-active b12x-flare-production.service b12x-flare-production-watchdog.timer b12x-flare-tailscale.service > "$w/final-production-active.txt"
date -u +%FT%TZ > "$w/adoption-closed.txt"
