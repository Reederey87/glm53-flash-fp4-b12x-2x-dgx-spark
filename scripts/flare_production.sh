#!/usr/bin/env bash
# Invoked only by the pinned production owner after qualification or explicit approval.
set -euo pipefail
ROOT=/home/nvidia/b12x-flare
[[ $(hostname) == spark-a183 ]]
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
    [[ ! -e "$ROOT/local/production-maintenance" ]]
    "$uv" run --offline --no-project --python /usr/bin/python3 "$ROOT/scripts/flare_production.py" verify
    ready=0
    peer_deadline=$((SECONDS + 600))
    while [[ $SECONDS -lt $peer_deadline ]]; do
        if "${peer[@]}" true; then ready=1; break; fi
        sleep 5
    done
    [[ $ready == 1 ]]
    "${peer[@]}" "$uv" run --offline --no-project --python /usr/bin/python3 "$ROOT/scripts/flare_production.py" verify --rank 1
    # Conflicting incumbent ownership is an error, not permission to stop it.
    ! systemctl --user is-enabled --quiet vllm-b12x.service
    ! systemctl --user is-active --quiet vllm-b12x.service
    [[ -z $(docker ps -q --filter name=vllm_node) ]]
    [[ -z $("${peer[@]}" docker ps -q --filter name=vllm_node) ]]
    /bin/bash "$ROOT/scripts/flare_production.sh" stop
    "$uv" run --offline --no-project --python /usr/bin/python3 "$ROOT/scripts/flare_release_file_cache.py"
    "${peer[@]}" "$uv" run --offline --no-project --python /usr/bin/python3 "$ROOT/scripts/flare_release_file_cache.py"
    # Flare sizes KV from MemAvailable, which counts reclaimable page cache on
    # GB10. Flush first so the pool is larger and repeatable; missing helper is
    # a warning, never a failed start.
    sudo -n /usr/local/sbin/b12x-drop-caches \
        || echo '[b12x] cache flush helper unavailable; startup pool may be smaller' >&2
    ENV_FILE=/home/nvidia/b12x/.env "$ROOT/scripts/wait_memory.sh" 600 </dev/null
    "$uv" run --offline --no-project --python /usr/bin/python3 "$ROOT/scripts/flare_production.py" start-ranks
    "$uv" run --offline --no-project --python /usr/bin/python3 "$ROOT/scripts/flare_production.py" ready
    # Warm and verify the actual API, including default reasoning and recovery.
    snapshot=/home/nvidia/.cache/huggingface/hub/models--nvidia--GLM-5.3-Flash-FP4-Local/snapshots/76348ddb2be2e35e39ecfc00e75dc07703f4f3d5
    timeout --signal=TERM --kill-after=15s 420 "$uv" run --offline --no-project --python "$ROOT/upstream/flare/.venv/bin/python" \
        "$ROOT/scripts/flare_smoke.py" --base http://127.0.0.1:8001 --snapshot "$snapshot" \
        --cancel-wait 180 \
        --out "$ROOT/local/production-smoke-${INVOCATION_ID:?}.json"
    ;;
 *) echo 'Expected start or stop' >&2; exit 2 ;;
esac
