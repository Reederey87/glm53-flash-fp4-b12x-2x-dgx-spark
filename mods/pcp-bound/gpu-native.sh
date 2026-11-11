#!/usr/bin/env bash
set -euo pipefail
case "${1-}" in indexed|unindexed) ;; *) exit 64 ;; esac
[[ "${2-}" =~ ^[0-9a-f]{32}$ ]] || exit 64
case "${3-}" in head|worker) ;; *) exit 64 ;; esac
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.."
sha256sum -c .pcp-frozen.sha256
test -z "$(docker ps -q)"
test "$(systemctl --user show vllm-b12x.service -p MainPID --value)" = 0
image=sha256:3b5da79c42ed4204440cfb07c6de1eba46441d5cba6b57d5428d44e60c10d0ed
test "$(docker image inspect "$image" --format '{{.Id}}')" = "$image"
name=b12x-pcp-native-${3}-${1}-${2}
test -z "$(docker ps -aq --filter name=^/${name}$)"
cleanup() {
 status=$?; trap - EXIT
 owned=$(timeout 5s docker ps -aq --filter name=^/${name}$) || { echo 'Probe cleanup inspection failed' >&2; exit 1; }
 if test -n "$owned"; then
  timeout --kill-after=5s 20s docker rm -f "$name" || { echo 'Probe cleanup failed; controller recovery required' >&2; exit 1; }
 fi
 exit "$status"
}
trap cleanup EXIT
# Creation is serialized with lease closure. Before releasing the lock, the
# stopped immutable container ID is visible to rollback's labelled scan. A late
# start by that ID fails if rollback already removed it; no late GPU admission.
exec 9>.pcp-lock
flock -x -w 5 9
test "$(cat .pcp-lease)" = armed
test "$(cat /proc/sys/vm/percpu_pagelist_high_fraction)" = 512
container=$(timeout --kill-after=5s 20s docker create --rm --name "$name" --label "b12x.pcp.stage=$PWD" \
 --gpus all --ipc host --network none --ulimit memlock=-1:-1 \
 -e CUTE_DSL_ARCH=sm_121a -e PYTORCH_CUDA_ALLOC_CONF= -e PYTORCH_ALLOC_CONF= \
 -e PYTORCH_HIP_ALLOC_CONF= -e PYTHONOPTIMIZE=0 \
 -v "$PWD:/probe:ro" -v /home/nvidia/.cache/b12x:/root/.cache/b12x \
 --entrypoint bash "$image" /probe/mods/pcp-bound/run-native.sh "$1" "$2" "$3")
[[ "$container" =~ ^[0-9a-f]{64}$ ]] || exit 65
flock -u 9
exec 9>&-
timeout --signal=TERM --kill-after=10s 60s docker start --attach "$container"
test -z "$(docker ps -aq --filter name=^/${name}$)"
