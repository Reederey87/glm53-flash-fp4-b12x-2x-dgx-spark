#!/usr/bin/env bash
set -euo pipefail
cd /home/nvidia/b12x-staging/pcp-bound-45fcfce
image=sha256:3b5da79c42ed4204440cfb07c6de1eba46441d5cba6b57d5428d44e60c10d0ed
temporary=$(mktemp /tmp/b12x-worker-read.XXXXXX)
trap 'rm -f "$temporary"' EXIT
docker run --rm --network none --entrypoint cat "$image" \
 /usr/local/lib/python3.12/dist-packages/vllm/v1/worker/gpu_worker.py > "$temporary"
printf '%s  %s\n' 668921c635ad810bfdb93a937ffa54a051859e5466cb8d941e1cb67e3e172e81 "$temporary" | sha256sum -c -
mv "$temporary" /tmp/b12x-pinned-gpu-worker.py
/home/nvidia/.local/bin/uv run --offline --no-project --python /usr/bin/python3 scripts/test_native_ownership.py
