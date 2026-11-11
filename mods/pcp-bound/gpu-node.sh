#!/usr/bin/env bash
set -euo pipefail
case "${1-}" in 0|512) ;; *) exit 64 ;; esac
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.."
sha256sum -c .pcp-frozen.sha256
test -z "$(docker ps -q)"
test "$(systemctl --user show vllm-b12x.service -p MainPID --value)" = 0
test "$(cat /proc/sys/vm/percpu_pagelist_high_fraction)" = "$1"
image=sha256:3b5da79c42ed4204440cfb07c6de1eba46441d5cba6b57d5428d44e60c10d0ed
test "$(docker image inspect "$image" --format '{{.Id}}')" = "$image"
name=b12x-pcp-micro-${1}
test -z "$(docker ps -aq --filter name=^/${name}$)"
trap 'docker rm -f "$name" >/dev/null 2>&1 || true' EXIT
timeout --signal=TERM --kill-after=10s 60s docker run --rm --name "$name" \
 --gpus all --ipc host --network none --ulimit memlock=-1:-1 \
 -e CUTE_DSL_ARCH=sm_121a -e PYTORCH_CUDA_ALLOC_CONF= -e PYTORCH_ALLOC_CONF= \
 -e PYTORCH_HIP_ALLOC_CONF= -e PYTHONOPTIMIZE=0 \
 -v "$PWD:/probe:ro" -v /home/nvidia/.cache/b12x:/root/.cache/b12x \
 --entrypoint bash "$image" /probe/mods/pcp-bound/run-micro.sh "$1"
test -z "$(docker ps -aq --filter name=^/${name}$)"
