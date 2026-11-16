#!/bin/bash
set -euo pipefail
w=/home/nvidia/b12x-flare/local/production-adoption-20261116T113000Z/retry-20261116T120500Z
unit=b12x-flare-production-adopt-20261116T120500Z.service
end=$((SECONDS+900))
while [[ $(systemctl --user show "$unit" -p MainPID --value) != 0 ]]; do
 [[ $SECONDS -lt $end ]]
 sleep 2
done
[[ $(systemctl --user show "$unit" -p ExecMainCode --value) == 1 ]]
[[ $(systemctl --user show "$unit" -p ExecMainStatus --value) == 0 ]]
/bin/bash "$w/verify-live.sh" activation
/bin/bash "$w/verify-watchdog.sh"
