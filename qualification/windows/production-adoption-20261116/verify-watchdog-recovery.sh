#!/bin/bash
# One controlled worker stop tests the production owner watchdog recovery.
set -Eeuo pipefail
r=/home/nvidia/b12x-flare
w=$r/local/production-adoption-20261116T113000Z/retry-20261116T120000Z
trap 'systemctl --user start --no-block b12x-flare-production-immediate-restore-20261116T113000Z.service' ERR
[[ -f "$w/activation-verified.txt" ]]
systemctl --user is-active --quiet b12x-flare-production-memory-20261116T120000Z.service
systemctl --user is-active --quiet b12x-flare-production-rollback.timer
systemctl --user is-active --quiet b12x-flare-production.service
owner=$(systemctl --user show b12x-flare-production.service -p InvocationID --value)
printf '%s\n' "$owner" > "$w/watchdog-owner-before.txt"
cp "$r/local/production-watchdog/state.json" "$w/watchdog-ledger-before.json"
ssh -n nvidia@192.168.177.11 systemctl --user show b12x-flare@1.service -p InvocationID -p MainPID > "$w/watchdog-worker-before.txt"
date -u +%FT%TZ > "$w/watchdog-injection-time.txt"
ssh -n nvidia@192.168.177.11 systemctl --user stop b12x-flare@1.service
end=$((SECONDS+1200)); recovered=0
while [[ $SECONDS -lt $end ]]; do
 now=$(systemctl --user show b12x-flare-production.service -p InvocationID --value)
 state=$(systemctl --user show b12x-flare-production.service -p ActiveState --value)
 [[ $state != failed ]]
 if [[ $now != "$owner" && $state == active ]]; then recovered=1; break; fi
 sleep 5
done
[[ $recovered == 1 ]]
/bin/bash "$w/verify-live.sh" watchdog
/home/nvidia/.local/bin/uv run --offline --no-project --python /usr/bin/python3 python - "$w" <<'PY'
import json,sys
from pathlib import Path
w=Path(sys.argv[1]);before=json.loads((w/'watchdog-ledger-before.json').read_text());after=json.loads((w/'watchdog-watchdog-ledger.json').read_text())
assert len(after['attempts'])==len(before['attempts'])+1,(before,after)
PY
journalctl --user -u b12x-flare-production-watchdog.service --since '2026-11-16 11:45:00 UTC' --no-pager > "$w/watchdog-journal.txt"
date -u +%FT%TZ > "$w/watchdog-recovery-complete.txt"
