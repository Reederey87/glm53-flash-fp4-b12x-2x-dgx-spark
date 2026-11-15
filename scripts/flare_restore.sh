#!/usr/bin/env bash
# Head-only restoration; also suitable for a pre-armed systemd rollback timer.
set -euo pipefail
ROOT=/home/nvidia/b12x-flare
[[ "$(hostname)" == spark-a183 ]]
exec 9>"$ROOT/local/restore.lock"
flock -n 9 || exit 0
units=(b12x-flare-build@0.service b12x-flare-prepare@0.service b12x-flare@0.service)
for unit in "${units[@]}"; do
    if systemctl --user cat "$unit" >/dev/null 2>&1; then systemctl --user stop "$unit"; fi
done
ssh -n -o BatchMode=yes -o ConnectTimeout=10 nvidia@192.168.177.11 \
    'set -e; for unit in b12x-flare-build@1.service b12x-flare-prepare@1.service b12x-flare@1.service; do if systemctl --user cat "$unit" >/dev/null 2>&1; then systemctl --user stop "$unit"; fi; done'
# Completed core reads can leave enough page cache to fail the strict MemFree
# gate. Advise only candidate files, after both ranks stop; never delete data or
# relax the incumbent's memory requirement. The helper also checks the GPU lock.
/home/nvidia/.local/bin/uv run --offline --no-project --python /usr/bin/python3 \
    "$ROOT/scripts/flare_release_file_cache.py" > "$ROOT/local/cache-release-before-restore.json"
ssh -n -o BatchMode=yes -o ConnectTimeout=10 nvidia@192.168.177.11 \
    '/home/nvidia/.local/bin/uv run --offline --no-project --python /usr/bin/python3 /home/nvidia/b12x-flare/scripts/flare_release_file_cache.py > /home/nvidia/b12x-flare/local/cache-release-before-restore.json'
# The incumbent unit already owns both-node teardown, memory and health gates.
systemctl --user reset-failed vllm-b12x.service
systemctl --user start vllm-b12x.service
curl --fail --silent --show-error --max-time 10 http://127.0.0.1:8000/health >/dev/null
if [[ -f "$ROOT/local/watchdog-was-active" ]]; then
    systemctl --user start vllm-b12x-watchdog.timer
fi
printf '%s B12X restored, health HTTP 200\n' "$(date -u +%FT%TZ)" | tee -a "$ROOT/local/window-ledger.txt"
