#!/usr/bin/env bash
# Per-rank operator qualification on an idle Spark; not a serving implementation.
set -euo pipefail
ROOT=/home/nvidia/b12x-flare
rank=${1:?rank required}
[[ "$rank" == 0 || "$rank" == 1 ]]
[[ "$(id -un)" == nvidia && "$(uname -m)" == aarch64 ]]
source "$ROOT/scripts/flare_env.sh"
exec 9>"$ROOT/local/gpu-operation.lock"
flock -n 9
[[ -z "$(docker ps -q --filter 'name=^/vllm_node$')" ]]
uv run --offline --no-project --python /usr/bin/python3 "$ROOT/scripts/flare_candidate.py" preflight --rank "$rank"
cd "$ROOT/upstream/flare"
sha256sum --check "$ROOT/local/build.sha256"
# Keep the serving CLI and installed preparation extension unchanged. The new
# feature artifact is copied into a private import path used only by this unit.
export PYO3_PYTHON="$PWD/.venv/bin/python"
cargo build --offline --release --locked --manifest-path heliopause/Cargo.toml \
    --features qualification,extension-module
RUN_DIR="$ROOT/local/qualification/$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir -p "$ROOT/qualification/native"
mkdir -p "$RUN_DIR"
printf "Qualification receipts: %s\n" "$RUN_DIR"
cp heliopause/target/release/libflare_heliopause.so "$ROOT/qualification/native/flare_heliopause.so.next"
mv "$ROOT/qualification/native/flare_heliopause.so.next" "$ROOT/qualification/native/flare_heliopause.so"
sha256sum "$ROOT/qualification/native/flare_heliopause.so" > "$RUN_DIR/extension.sha256"
sha256sum --check "$ROOT/local/build.sha256"
export CUDA_VISIBLE_DEVICES=0 FLARE_RUN_CUDA_TESTS=1
export FLARE_GLM53_SNAPSHOT=/home/nvidia/.cache/huggingface/hub/models--nvidia--GLM-5.3-Flash-FP4-Local/snapshots/76348ddb2be2e35e39ecfc00e75dc07703f4f3d5
export PYTHONPATH="$ROOT/qualification/native:$PWD"
uv run --offline --no-sync python -c 'import flare_heliopause; print("Qualification extension:", flare_heliopause.__file__); assert flare_heliopause.__file__.startswith("/home/nvidia/b12x-flare/qualification/native/")'
# Keep all result sets even if one fails. A nonzero outcome fails the unit.
result=0
timeout --signal=TERM --kill-after=30s 1800 uv run --offline --no-sync python -m pytest \
    -q -s tests/recipes/test_glm53_indexer_cuda.py \
    --junitxml="$RUN_DIR/indexer.xml" || result=1
timeout --signal=TERM --kill-after=30s 1800 uv run --offline --no-sync python -m pytest \
    -q -s "$ROOT/qualification/test_glm53_state_cuda.py" \
    --junitxml="$RUN_DIR/kda.xml" || result=1
timeout --signal=TERM --kill-after=30s 600 uv run --offline --no-sync python -m pytest \
    -q -s tests/recipes/test_glm53_state_transfer_cuda.py \
    --junitxml="$RUN_DIR/state-transfer.xml" || result=1
# A skip is missing qualification evidence, even if pytest exits zero.
uv run --offline --no-project --python /usr/bin/python3 - "$RUN_DIR" <<'PY'
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
root = Path(sys.argv[1])
for name, expected in [('indexer.xml', 4), ('kda.xml', 2), ('state-transfer.xml', 32)]:
    cases = ET.parse(root / name).findall('.//testcase')
    if len(cases) != expected or any(any(c.find(tag) is not None for tag in ('skipped','failure','error')) for c in cases):
        raise SystemExit(f'{name}: expected {expected} executed passing cases')
print('All 38 numerical/replay/state-transfer cases executed and passed')
PY
exit "$result"
