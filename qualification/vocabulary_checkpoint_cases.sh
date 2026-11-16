#!/bin/bash
# Keep upstream's fresh GPU process per indexed mode, on each of the two hosts.
set -euo pipefail
r=/home/nvidia/b12x-flare
out=${1:?new receipt directory required}
uv=/home/nvidia/.local/bin/uv
for capacity in False True; do
 "$uv" run --offline --no-project --python /usr/bin/python3 python - "$out/memory-before-$capacity.json" <<'PY'
import json, os, sys, time
from pathlib import Path
deadline = time.monotonic() + 60
while True:
    values = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key, _, rest = line.partition(':')
        if key in ('MemFree', 'MemAvailable'):
            amount, unit = rest.split()
            assert unit == 'kB'
            values[key] = int(amount) * 1024
    if values['MemFree'] >= 90*(1<<30) and values['MemAvailable'] >= 100*(1<<30):
        Path(sys.argv[1]).write_text(json.dumps({'time': time.time(), 'gate_pid': os.getpid(),
                                                'memory': values})+'\n')
        break
    if time.monotonic() >= deadline:
        raise RuntimeError(f'fresh-process idle memory gate failed: {values}')
    time.sleep(2)
PY
 "$uv" run --offline --no-project --python "$r/upstream/flare/.venv/bin/python" python -m pytest \
  -x -q -s "$r/qualification/test_vocabulary_checkpoint_cuda.py::test_checkpoint_vocabulary_replay[$capacity]" \
  --junitxml="$out/vocabulary-$capacity.xml" &
 child=$!
 printf '%s %s\n' "$capacity" "$child" >> "$out/case-processes.txt"
 set +e
 wait "$child"
 status=$?
 set -e
 printf '%s\n' "$status" > "$out/pytest-exit-$capacity.txt"
 [[ $status == 0 ]] || exit "$status"
done
