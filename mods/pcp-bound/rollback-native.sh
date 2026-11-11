#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.."
# Close application first, without changing PCP, under the setter's same lock.
if test -f .pcp-lease; then
 timeout 10s flock -x -w 5 .pcp-lock /bin/sh -c 'printf "closed\n" > "$1"' sh .pcp-lease
fi
# Remove only this private trial's disposable GPU processes before restoring0.
owned=$(timeout 5s docker ps -aq --filter "label=b12x.pcp.stage=$PWD")
if test -n "$owned"; then
 while IFS= read -r container; do
  [[ "$container" =~ ^[0-9a-f]{12,64}$ ]] || exit 65
  timeout --kill-after=5s 20s docker rm -f "$container"
 done <<< "$owned"
fi
test -z "$(timeout 5s docker ps -aq --filter "label=b12x.pcp.stage=$PWD")"
exec bash mods/pcp-bound/rollback.sh
