#!/usr/bin/env bash
# Invoked only by the pinned production owner after qualification or explicit approval.
set -euo pipefail
ROOT=/home/nvidia/b12x-flare
[[ $(hostname) == spark-a183 ]] || { echo '[b12x] wrong host for the owner' >&2; exit 78; }
uv=/home/nvidia/.local/bin/uv
peer=(ssh -n -o BatchMode=yes -o ConnectTimeout=5 nvidia@192.168.177.11)
case "${1:-}" in
 stop)
    # ExecStopPost also runs after partial/failed startup. Clean both ranks,
    # including a worker left behind before the head supervisor was created.
    status=0
    systemctl --user stop b12x-flare@0.service || status=1
    "${peer[@]}" systemctl --user stop b12x-flare@1.service || status=1
    exit "$status"
    ;;
 start)
    # Only the readiness shortfall decides retryability, and it signals 75. Every
    # other failure here is terminal (78), so a broken start cannot consume the
    # unit's restart budget.
    trap 'rc=$?; if [[ $rc -eq 75 ]]; then
              marker="$ROOT/local/production-startup-retry/retry-${INVOCATION_ID:-none}"
              [[ -f $marker ]] || { echo "[b12x] exit 75 without a ledger receipt" >&2; exit 78; }
          elif [[ $rc -ne 0 ]]; then
              echo "[b12x] start failed rc=$rc; not retrying" >&2; exit 78
          fi' EXIT
    [[ ! -e "$ROOT/local/production-maintenance" ]]
    timeout 90 "$uv" run --offline --no-project --python /usr/bin/python3 "$ROOT/scripts/flare_production.py" verify
    ready=0
    peer_deadline=$((SECONDS + 600))
    while [[ $SECONDS -lt $peer_deadline ]]; do
        if timeout 30 "${peer[@]}" true; then ready=1; break; fi
        sleep 5
    done
    [[ $ready == 1 ]]
    timeout 90 "${peer[@]}" "$uv" run --offline --no-project --python /usr/bin/python3 "$ROOT/scripts/flare_production.py" verify --rank 1
    # Conflicting incumbent ownership is an error, not permission to stop it.
    ! systemctl --user is-enabled --quiet vllm-b12x.service
    ! systemctl --user is-active --quiet vllm-b12x.service
    [[ -z $(timeout 30 docker ps -q --filter name=vllm_node) ]]
    # An SSH failure here must not look like "no containers".
    peer_containers=$(timeout 30 "${peer[@]}" docker ps -q --filter name=vllm_node) \
        || { echo '[b12x] cannot inspect the worker for incumbent containers' >&2; exit 78; }
    [[ -z $peer_containers ]]
    timeout 420 /bin/bash "$ROOT/scripts/flare_production.sh" stop
    timeout 300 "$uv" run --offline --no-project --python /usr/bin/python3 "$ROOT/scripts/flare_release_file_cache.py"
    timeout 300 "${peer[@]}" "$uv" run --offline --no-project --python /usr/bin/python3 "$ROOT/scripts/flare_release_file_cache.py"
    # Flare sizes KV from MemAvailable (which counts reclaimable page cache on
    # GB10) and negotiates the smallest capacity any rank can back, so prepare
    # BOTH ranks. A missing helper only warns; it never fails a start.
    timeout 90 sudo -n /usr/local/sbin/b12x-drop-caches \
        || echo '[b12x] cache flush unavailable or incomplete on head; pool may be smaller' >&2
    timeout 90 "${peer[@]}" sudo -n /usr/local/sbin/b12x-drop-caches \
        || echo '[b12x] cache flush unavailable or incomplete on worker; pool may be smaller' >&2
    timeout 620 env ENV_FILE=/home/nvidia/b12x/.env "$ROOT/scripts/wait_memory.sh" 600 </dev/null
    # Evidence for the pool draw, taken after the gate and immediately before
    # dispatch, so it reflects the memory the ranks actually size from. Best
    # effort: a storage or SSH failure must not fail an otherwise sound start.
    if [[ ${INVOCATION_ID:-} =~ ^[0-9a-f]{32}$ ]]; then
        memdir="$ROOT/local/startup-memory-$INVOCATION_ID"
        if mkdir -p "$memdir"; then
            cp /proc/meminfo "$memdir/head-meminfo.txt" 2>/dev/null || true
            cp /proc/sys/vm/min_free_kbytes "$memdir/head-min-free-kbytes.txt" 2>/dev/null || true
            timeout 30 "${peer[@]}" cat /proc/meminfo > "$memdir/worker-meminfo.txt" 2>/dev/null || true
            timeout 30 "${peer[@]}" cat /proc/sys/vm/min_free_kbytes \
                > "$memdir/worker-min-free-kbytes.txt" 2>/dev/null || true
            [[ -s "$memdir/worker-meminfo.txt" ]] || rm -f "$memdir/worker-meminfo.txt" || true
        fi
    fi
    timeout 180 "$uv" run --offline --no-project --python /usr/bin/python3 "$ROOT/scripts/flare_production.py" start-ranks
    timeout 960 "$uv" run --offline --no-project --python /usr/bin/python3 "$ROOT/scripts/flare_production.py" ready
    # Warm and verify the actual API, including default reasoning and recovery.
    snapshot=/home/nvidia/.cache/huggingface/hub/models--nvidia--GLM-5.3-Flash-FP4-Local/snapshots/76348ddb2be2e35e39ecfc00e75dc07703f4f3d5
    # Budget: 180 s idle wait + 120 s stream timeout + the remaining checks must
    # fit inside this wrapper, and every startup phase must fit TimeoutStartSec.
    smoke_rc=0
    timeout --signal=TERM --kill-after=15s 480 "$uv" run --offline --no-project --python "$ROOT/upstream/flare/.venv/bin/python" \
        "$ROOT/scripts/flare_smoke.py" --base http://127.0.0.1:8001 --snapshot "$snapshot" \
        --cancel-wait 180 \
        --out "$ROOT/local/production-smoke-${INVOCATION_ID:?}.json" || smoke_rc=$?
    if [[ $smoke_rc -ne 0 ]]; then
        # Only a budgeted capacity shortfall may be retried (exit 75). A failed or
        # timed-out smoke is terminal for the operator, not a restart candidate.
        echo "[b12x] startup smoke failed rc=$smoke_rc; not retrying" >&2
        exit 78
    fi
    ;;
 *) echo 'Expected start or stop' >&2; exit 2 ;;
esac
