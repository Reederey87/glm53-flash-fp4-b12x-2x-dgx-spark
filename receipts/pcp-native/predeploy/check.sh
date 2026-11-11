#!/usr/bin/env bash
set -euo pipefail
cd /home/nvidia/b12x-staging/pcp-bound-45fcfce
UV=/home/nvidia/.local/bin/uv
for file in test_kernel_memory_counters.py test_pinned_cache.py test_native_ownership.py; do
 "$UV" run --offline --no-project --python /usr/bin/python3 "scripts/$file"
done
unit=$(date -u +b12x-pcp512-rollback-%Y%m%dt%H%M%Sz)
trap 'systemctl --user stop "$unit.timer" >/dev/null 2>&1 || true' EXIT
systemd-run --user --unit="$unit" --on-active=600s --timer-property=AccuracySec=1s \
 --property=Restart=on-failure --property=RestartSec=5s --property=StartLimitIntervalSec=0 /bin/true
"$UV" run --offline --no-project --python /usr/bin/python3 scripts/check_pcp_timer.py "$unit" 540 600
"$UV" run --offline --no-project --python /usr/bin/python3 python -c \
 'import sys;sys.path.insert(0,"scripts");from run_pcp_micro import cancel_command;print(cancel_command(sys.argv[1]))' "$unit" | bash
! systemctl --user is-active --quiet "$unit.timer"
test "$(cat /proc/sys/vm/percpu_pagelist_high_fraction)" = 0
"$UV" run --offline --no-project --python /usr/bin/python3 scripts/pcp_bound_snapshot.py 0
echo 'NATIVE_PREFLIGHT_PASS policy0 unchanged'
