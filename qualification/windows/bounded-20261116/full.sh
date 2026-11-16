#!/bin/bash
set -Eeuo pipefail
r=/home/nvidia/b12x-flare
w=$r/local/bounded-window-20261116T041500Z
restore=b12x-flare-bounded-restore-20261116T041500Z.service
trap 'systemctl --user start --no-block "$restore"' ERR
uv=/home/nvidia/.local/bin/uv
arm=127424e92c1e5845697d85f3c34ce93fa632dd48bf3be491c868c50a9deb0243
binary=b2eb310b9ec9009fa499086777d9ed90105b323db70da527242286dc0de026b9
[[ -f "$w/mixed-gate-passed.txt" ]]
systemctl --user is-active --quiet b12x-flare-bounded-restore-20261116T041500Z.timer
systemctl --user is-active --quiet b12x-flare-bounded-memory-latency-20261116T041500Z.service
"$uv" run --offline --no-project --python /usr/bin/python3 "$w/verify-native.py" 0 latency "$arm" "$binary" > "$w/full-head-identity.json"
ssh -n nvidia@192.168.177.11 "$uv" run --offline --no-project --python /usr/bin/python3 "$w/verify-native.py" 1 latency "$arm" "$binary" > "$w/full-worker-identity.json"
[[ $(sha256sum "$w/reference-full-bench.jsonl" | cut -d ' ' -f1) == 84c2865f80cdbda06eaa5d86e9d577866a70ff3e4ed61da534b3420a867bfefd ]]
snap=/home/nvidia/.cache/huggingface/hub/models--nvidia--GLM-5.3-Flash-FP4-Local/snapshots/76348ddb2be2e35e39ecfc00e75dc07703f4f3d5
"$uv" run --offline --no-project --python /usr/bin/python3 "$r/scripts/flare_bench.py" \
    --base http://127.0.0.1:8001 --engine flare --tokenizer "$snap/tokenizer.json" \
    --out "$w/latency-full-bench.jsonl" --reps 3 --seed 20261115 \
    --lengths 8192,16384,32768,65536,131072 --concurrency 1,2,4,8 --decode-tokens 200 --slot-cap 4
printf 'full_matrix client_exit=0\n' >> "$w/client-exits.txt"
"$uv" run --offline --no-project --python /usr/bin/python3 "$r/scripts/flare_compare.py" \
    --reference "$w/reference-full-bench.jsonl" --candidate "$w/latency-full-bench.jsonl" --out "$w/full-comparison.json"
"$uv" run --offline --no-project --python /usr/bin/python3 python - "$w/full-comparison.json" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]);report=json.loads(p.read_text())
assert report['rows_per_arm']==84
bad=[{'point':{k:row[k] for k in ('kind','concurrency','point')},'metric':metric,**value}
     for row in report['points'] for metric,value in row['metrics'].items()
     if value['observation']!='no_median_regression_over_2pct_observed']
print(json.dumps({'points':len(report['points']),'requires_investigation':bad}),flush=True)
assert not bad,'Full performance gate needs investigation; restore before proceeding'
p.with_name('full-gate-passed.txt').write_text('Full matrix comparison passed; other adoption gates remain.\n')
PY
