#!/bin/bash
set -euo pipefail
r=/home/nvidia/b12x-flare
w=$r/local/memory-notify-probe-20261116T140000Z
mkdir "$w"
uv=/home/nvidia/.local/bin/uv
prefix=b12x-flare-notify-probe
stamp=20261116T140000Z
cleanup() {
 for role in healthy invalid hang; do systemctl --user stop "$prefix-$role-$stamp.service" || true; done
 for role in invalid hang; do systemctl --user stop "$prefix-$role-restore-$stamp.timer" "$prefix-$role-restore-$stamp.service" || true; done
}
trap cleanup EXIT
for role in invalid hang; do
 systemd-run --user --unit="$prefix-$role-restore-$stamp" --on-active=1h --property=Type=exec --property=RemainAfterExit=yes /usr/bin/touch "$w/$role-restored"
done
common=(--user --property=Type=notify --property=NotifyAccess=all --property=TimeoutStartSec=10 --property=LimitCORE=0)
systemd-run "${common[@]}" --unit="$prefix-healthy-$stamp" --property=WatchdogSec=8 --property=RemainAfterExit=yes "$uv" run --offline --no-project --python /usr/bin/python3 "$r/qualification/memory_notify_probe.py" healthy "$w/healthy.jsonl"
# Type=notify must not return before a healthy journal sample exists.
[[ -s "$w/healthy.jsonl" ]]
end=$((SECONDS+20))
while [[ $(systemctl --user show "$prefix-healthy-$stamp.service" -p MainPID --value) != 0 ]]; do [[ $SECONDS -lt $end ]]; sleep .2; done
[[ $(systemctl --user show "$prefix-healthy-$stamp.service" -p ExecMainCode --value) == 1 ]]
[[ $(systemctl --user show "$prefix-healthy-$stamp.service" -p ExecMainStatus --value) == 0 ]]
[[ $(wc -l < "$w/healthy.jsonl") == 2 ]]
set +e
systemd-run "${common[@]}" --unit="$prefix-invalid-$stamp" --property=WatchdogSec=2 --property=OnFailure="$prefix-invalid-restore-$stamp.service" "$uv" run --offline --no-project --python /usr/bin/python3 "$r/scripts/flare_memory_watch.py" --out "$w/invalid.jsonl" --restore-unit invalid
invalid_start=$?
set -e
[[ $invalid_start != 0 ]]
systemd-run "${common[@]}" --unit="$prefix-hang-$stamp" --property=WatchdogSec=2 --property=OnFailure="$prefix-hang-restore-$stamp.service" "$uv" run --offline --no-project --python /usr/bin/python3 "$r/qualification/memory_notify_probe.py" hang
end=$((SECONDS+20))
while [[ ! -e "$w/invalid-restored" || ! -e "$w/hang-restored" ]]; do [[ $SECONDS -lt $end ]]; sleep .2; done
[[ $(systemctl --user show "$prefix-invalid-$stamp.service" -p ExecMainStatus --value) == 2 ]]
[[ $(systemctl --user show "$prefix-hang-$stamp.service" -p Result --value) == watchdog ]]
for role in healthy invalid hang; do
 systemctl --user show "$prefix-$role-$stamp.service" -p Id -p InvocationID -p Result -p MainPID -p ExecMainCode -p ExecMainStatus -p Type -p NotifyAccess -p WatchdogUSec >> "$w/terminal.txt"
done
for role in invalid hang; do
 unit="$prefix-$role-restore-$stamp.service"
 [[ $(systemctl --user show "$unit" -p MainPID --value) == 0 ]]
 [[ $(systemctl --user show "$unit" -p ExecMainCode --value) == 1 ]]
 [[ $(systemctl --user show "$unit" -p ExecMainStatus --value) == 0 ]]
 systemctl --user show "$unit" -p Id -p InvocationID -p MainPID -p ExecMainCode -p ExecMainStatus >> "$w/terminal.txt"
done
date -u +%FT%TZ > "$w/probe-passed.txt"
cat "$w/terminal.txt" "$w/probe-passed.txt"
