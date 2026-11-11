#!/usr/bin/env bash
set -euo pipefail
cd /home/nvidia/b12x-staging/kernel-return-20bc183
test -z "$(docker ps -q)"
test "$(systemctl --user show vllm-b12x.service -p MainPID --value)" = 0
image=sha256:3b5da79c42ed4204440cfb07c6de1eba46441d5cba6b57d5428d44e60c10d0ed
test "$(docker image inspect "$image" --format '{{.Id}}')" = "$image"
sha256sum -c <<'HASHES'
9e48a369ddfa9e526da8531197a13e726b0e4d23b9d4318a16729a5f31d9a946  scripts/kernel_memory_counters.py
c26871699b934ca699895af90b9aa3b397d421e007f900d05c731841b09f1812  scripts/check_kernel_return_cuda.py
83f453006fc9aff77ec75a23a0a92cf5c58ad1ad68fd6fd3df5f37184c859642  scripts/check_host_register_memory_cuda.py
8e4e1a86aecc164d02fd8890951ab453adacf2eda4cf5d263d820480babf71ce  scripts/check_pinned_residency_cuda.py
57b36e834cd0b904de614f564c4051d488ac3090e7b128fe72bfcd9248890039  mods/startup-pinned/install.py
1761e9aeb863da2cb307fc7094c30af495aa78ff9e135e9d58d81df7b6c82ac6  mods/startup-pinned/release.py
efb9df3ef205e59e9469a99dc38d95363f90be1377ea94d0ed60e98ec70f23d8  run-paired.sh
HASHES
name=b12x-kernel-return-20bc183
test -z "$(docker ps -aq --filter name=^/${name}$)"
trap 'docker rm -f "$name" >/dev/null 2>&1 || true' EXIT
date -u +%FT%TZ
docker run --rm --name "$name" --gpus all --ipc host --network none --ulimit memlock=-1:-1 \
 -e CUTE_DSL_ARCH=sm_121a -e PYTORCH_CUDA_ALLOC_CONF= -e PYTORCH_ALLOC_CONF= \
 -e PYTORCH_HIP_ALLOC_CONF= -e PYTHONOPTIMIZE=0 \
 -v "$PWD:/probe:ro" -v /home/nvidia/.cache/b12x:/root/.cache/b12x \
 --entrypoint bash "$image" /probe/run-paired.sh
test -z "$(docker ps -aq --filter name=^/${name}$)"
date -u +%FT%TZ
