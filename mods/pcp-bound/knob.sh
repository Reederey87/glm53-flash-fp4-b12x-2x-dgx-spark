#!/usr/bin/env bash
set -euo pipefail
case "${1-}:${2-}" in 0:512|512:0) ;; *) exit 64 ;; esac
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.."
if test "$2" = 512; then
 test "$(uname -r)" = 6.17.0-1031-nvidia
 test "$(cat /proc/sys/vm/min_free_kbytes)" = 1048576
 test "$(cat /proc/sys/vm/stat_interval)" = 1
fi
image=sha256:3b5da79c42ed4204440cfb07c6de1eba46441d5cba6b57d5428d44e60c10d0ed
# Root Docker access writes only this explicit host sysctl bind. No privileged
# container, host namespaces, extra capabilities, persistent config or sysctl -p.
name=b12x-pcp-policy-${BASHPID}
trap 'timeout 10s docker rm -f "$name" >/dev/null 2>&1 || true' EXIT
timeout --kill-after=5s 20s docker run --rm --name "$name" --network none --pids-limit 32 --memory 128m --cpus 1 \
 --cap-drop ALL --security-opt no-new-privileges \
 -v /proc/sys/vm/percpu_pagelist_high_fraction:/knob:rw \
 -v "$PWD/.pcp-lock:/lock:rw" -v "$PWD/.pcp-lease:/lease:rw" \
 --entrypoint /usr/bin/flock "$image" -x -w 5 /lock /bin/sh -c \
 'set -eu
 if test "$2" = 0; then
   printf "closed\n" > /lease
   current=$(cat /knob)
   case "$current" in 0) exit 0 ;; 512) ;; *) exit 65 ;; esac
 else
   test "$(cat /lease)" = armed
   test "$(cat /knob)" = "$1"
 fi
 printf "%s\n" "$2" > /knob
 test "$(cat /knob)" = "$2"' sh "$1" "$2"
test "$(cat /proc/sys/vm/percpu_pagelist_high_fraction)" = "$2"
if test "$(cat /proc/sys/vm/min_free_kbytes)" != 1048576 || test "$(cat /proc/sys/vm/stat_interval)" != 1; then
 echo 'PCP restored/applied; unrelated controls drifted' >&2
fi
printf 'B12X_PCP_POLICY %s %s %s\n' "$1" "$2" "$(date -u +%FT%TZ)"
