#!/bin/bash
set -euo pipefail
r=/home/nvidia/b12x-flare
w=$r/local/production-adoption-20261116T113000Z/retry-20261116T120500Z
end=$((SECONDS+1200)); ready=0
while [[ $SECONDS -lt $end ]]; do
 state=$(systemctl --user show b12x-flare-production.service -p ActiveState --value)
 [[ $state != failed ]]
 if [[ $state == active ]]; then ready=1; break; fi
 sleep 3
done
[[ $ready == 1 ]]
/bin/bash "$w/verify-live.sh" reboot
uname -r > "$w/reboot-head-kernel-after.txt"
nvidia-smi --query-gpu=driver_version --format=csv,noheader > "$w/reboot-head-driver-after.txt"
ssh -n nvidia@192.168.177.11 uname -r > "$w/reboot-worker-kernel-after.txt"
ssh -n nvidia@192.168.177.11 nvidia-smi --query-gpu=driver_version --format=csv,noheader > "$w/reboot-worker-driver-after.txt"
/home/nvidia/.local/bin/uv run --offline --no-project --python /usr/bin/python3 python - "$w" <<'PY'
import json,sys
from pathlib import Path
w=Path(sys.argv[1])
for rank in ('head','worker'):
 assert (w/f'reboot-{rank}-before.txt').read_text().strip() != (w/f'reboot-{rank}-boot.txt').read_text().strip()
 for field in ('kernel','driver'):
  assert (w/f'reboot-{rank}-{field}-before.txt').read_text() == (w/f'reboot-{rank}-{field}-after.txt').read_text()
before=json.loads((w/'watchdog-watchdog-ledger.json').read_text())
after=json.loads((w/'reboot-watchdog-ledger.json').read_text())
assert before['attempts']==after['attempts'],(before,after)
PY
journalctl --user -b -u b12x-flare-production.service -u b12x-flare-production-watchdog.service -u b12x-flare-tailscale.service --no-pager -o short-iso > "$w/reboot-owner-journal.txt"
date -u +%FT%TZ > "$w/reboot-verification-complete.txt"
