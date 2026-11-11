#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.."
if ! test -f .pcp-lease; then
 test "$(cat /proc/sys/vm/percpu_pagelist_high_fraction)" = 0
 echo 'B12X_PCP_ROLLBACK never-armed'
 exit 0
fi
# Always close the lease under the shared lock, even when policy is already0.
# A delayed apply container then cannot write512 after this restoration.
bash mods/pcp-bound/knob.sh 512 0
