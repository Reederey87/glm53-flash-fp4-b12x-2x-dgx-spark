#!/usr/bin/env bash
# Run only through b12x-flare-build@.service, after the two-node window gate.
set -euo pipefail
ROOT=/home/nvidia/b12x-flare
rank="${1:?rank required}"
[[ "$rank" == 0 || "$rank" == 1 ]]
[[ "$(id -un)" == nvidia && "$(uname -m)" == aarch64 ]]
source "$ROOT/scripts/flare_env.sh"
exec 9>"$ROOT/local/gpu-operation.lock"
flock -n 9
[[ -z "$(docker ps -q --filter name='^/vllm_node$')" ]] || { echo 'Incumbent container is running' >&2; exit 1; }
uv run --offline --no-project --python /usr/bin/python3 "$ROOT/scripts/flare_candidate.py" preflight --rank "$rank"
cd "$ROOT/upstream/flare"
uv sync --locked --extra prepare --extra test --python /home/nvidia/.local/share/uv/python/cpython-3.12.14-linux-aarch64-gnu/bin/python3
cargo build --release --locked --manifest-path flare-cli/Cargo.toml
flare-cli/target/release/flare --help > "$ROOT/local/flare-help.txt"
uv run --no-sync python "$ROOT/scripts/flare_cuda_probe.py" > "$ROOT/local/cuda-probe.json"
sha256sum flare-cli/target/release/flare uv.lock flare-cli/Cargo.lock heliopause/Cargo.lock > "$ROOT/local/build.sha256"
printf 'Build and CUDA probe passed for rank %s\n' "$rank"
