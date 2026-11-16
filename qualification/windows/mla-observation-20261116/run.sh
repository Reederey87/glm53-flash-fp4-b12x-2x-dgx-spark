#!/bin/bash
set -Eeuo pipefail
r=/home/nvidia/b12x-flare
w=$r/local/mla-observation-window-20261116T073000Z
restore=b12x-flare-mla-observation-restore-20261116T073000Z.service
trap 'systemctl --user start --no-block "$restore"' ERR
uv=/home/nvidia/.local/bin/uv
systemctl --user is-active --quiet b12x-flare-mla-observation-restore-20261116T073000Z.timer
sha256sum --check "$w/runtime-source.sha256"
curl --fail --silent --max-time 10 http://127.0.0.1:8000/metrics > "$w/incumbent-before.metrics"
"$uv" run --offline --no-project --python /usr/bin/python3 python - "$w/incumbent-before.metrics" <<'PY'
import sys
from pathlib import Path
rows=[x for x in Path(sys.argv[1]).read_text().splitlines()
      if x.startswith(('vllm:num_requests_running{','vllm:num_requests_waiting{'))]
assert len(rows)>=2 and all(float(x.rsplit(' ',1)[1])==0 for x in rows)
PY
systemctl --user stop vllm-b12x-watchdog.timer vllm-b12x.service
[[ -z $(docker ps -q --filter name=vllm_node) ]]
[[ -z $(ssh -n nvidia@192.168.177.11 docker ps -q --filter name=vllm_node) ]]
ENV_FILE=/home/nvidia/b12x/.env "$r/scripts/wait_memory.sh" 600 </dev/null
systemd-run --user --unit=b12x-flare-mla-observation-memory-20261116T073000Z --property=Type=exec --property=RuntimeMaxSec=3400 \
  "$uv" run --offline --no-project --python /usr/bin/python3 "$r/scripts/flare_memory_watch.py" \
  --out "$w/memory.jsonl" --seconds 3400 --restore-unit "$restore"
/bin/bash "$r/qualification/run_native_mla.sh" "$w/results"
sha256sum --check "$w/head-before.sha256" > "$w/unchanged-runtime-after.txt"
ssh -n nvidia@192.168.177.11 "sha256sum --check $w/worker-before.sha256" >> "$w/unchanged-runtime-after.txt"
printf '%s All6 pinned native-activation MLA replay cases passed; full-model gates remain.\n' "$(date -u +%FT%TZ)" > "$w/mla-gate-passed.txt"
systemctl --user stop b12x-flare-mla-observation-memory-20261116T073000Z.service
systemctl --user start --no-block "$restore"
