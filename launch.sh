#!/usr/bin/env bash
# ============================================================================
# launch.sh — b12x kit: GLM-5.3-Flash-FP4-Local on 2x DGX Spark
# ============================================================================
# Usage:
#   ./launch.sh                  start both ranks (preflight, then recipe)
#   ./launch.sh down [--if-owned] stop both ranks (idempotent; --if-owned only
#                                 touches a tree this kit started)
#   ./launch.sh restart          down, wait for memory, start
#   ./launch.sh status           containers, image identity, /health, model, KV
#   ./launch.sh logs [worker]    follow the head (or worker) container log
#   ./launch.sh render           print the exact generated command
#   ./launch.sh preflight        read-only host/cluster checks
#   ./launch.sh setup            prepare image + checkpoint only (no serve)
#   ./launch.sh smoke            functional API checks (incl. max reasoning)
#   ./launch.sh speed [--gate]   prefill ladder + decode matrix + acceptance
#   ./launch.sh qualify          compatibility matrix -> receipts/
#
# Production runs through systemd/vllm-b12x.service, which owns the memory and
# health gates. Caller-exported values win over .env for the keys in CAPTURE.
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"
RECIPE="$SCRIPT_DIR/recipes/glm-5.3-flash-fp4-local.yaml"
MODEL_ID="nvidia/GLM-5.3-Flash-FP4-Local"
CHECKPOINT_REV="76348ddb2be2e35e39ecfc00e75dc07703f4f3d5"
OWNED_MARKER="$SCRIPT_DIR/local/kit-owned"

log()  { printf '\033[1;36m[b12x]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[b12x]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[b12x]\033[0m %s\n' "$*" >&2; exit 1; }

usage() { sed -n '4,22p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

# Keys a caller may override around `.env` (documented precedence).
CAPTURE=(PORT HOST MAX_MODEL_LEN GPU_MEMORY_UTILIZATION CLUSTER_NODES HEAD_IP
         WORKER_IP ETH_IF IB_IF COPY_HOSTS MASTER_PORT CONTAINER_NAME IMAGE_TAG
         IMAGE_REF PULL_IMAGE SPARK_VLLM_REF SPARK_VLLM_DIR HF_TOKEN TAIL
         DEFAULT_REASONING_EFFORT)

load_env() {
    if [ ! -f "$ENV_FILE" ]; then
        [ -f "$SCRIPT_DIR/env.example" ] || die "missing env.example"
        cp "$SCRIPT_DIR/env.example" "$ENV_FILE"
        die "wrote $ENV_FILE from env.example — edit CLUSTER_NODES/WORKER_IP, then rerun"
    fi
    local -a saved=()
    local k
    for k in "${CAPTURE[@]}"; do
        [ -n "${!k+x}" ] && saved+=("$k=${!k}")
    done
    set -a
    # shellcheck disable=SC1090
    . "$ENV_FILE"
    set +a
    for k in "${saved[@]}"; do export "$k"; done

    : "${SPARK_VLLM_DIR:=$SCRIPT_DIR/.vendor/spark-vllm-docker}"
    case "$SPARK_VLLM_DIR" in /*) ;; *) SPARK_VLLM_DIR="$SCRIPT_DIR/$SPARK_VLLM_DIR" ;; esac
    : "${SPARK_VLLM_REF:=0bdc9c94cd89843e1c8f7d7b33df2d5bc746c03d}"
    : "${IMAGE_REF:=eugr/spark-vllm-b12x:nightly-20261015}"
    : "${IMAGE_TAG:=vllm-node-b12x}"
    : "${CONTAINER_NAME:=vllm_node}"
    : "${PORT:=8000}"
    : "${HOST:=127.0.0.1}"
    : "${MAX_MODEL_LEN:=1000000}"
    : "${GPU_MEMORY_UTILIZATION:=0.87}"
    : "${MASTER_PORT:=29501}"
    : "${PULL_IMAGE:=0}"
    : "${TAIL:=200}"
    : "${HEAD_IP:=}"
    : "${WORKER_IP:=}"
    : "${DEFAULT_REASONING_EFFORT:=max}"
    : "${HF_TOKEN:=}"
    export CLUSTER_NODES ETH_IF IB_IF COPY_HOSTS MASTER_PORT IMAGE_TAG IMAGE_REF \
           PULL_IMAGE CONTAINER_NAME PORT HOST MAX_MODEL_LEN GPU_MEMORY_UTILIZATION \
           HEAD_IP WORKER_IP DEFAULT_REASONING_EFFORT HF_TOKEN
    [ -f "$RECIPE" ] || die "missing recipe: $RECIPE"
    [ -n "$HEAD_IP" ] || die "HEAD_IP is required"
    [ -n "$WORKER_IP" ] || die "WORKER_IP is required (cluster_only recipe)"
    local recipe_container
    recipe_container="$(awk '/^container:/{print $2; exit}' "$RECIPE")"
    [ "$recipe_container" = "$IMAGE_TAG" ] \
        || die "recipe container '$recipe_container' != IMAGE_TAG '$IMAGE_TAG'"
}

node_list() { local IFS=','; local -a n=($CLUSTER_NODES); printf '%s\n' "${n[@]}"; }

ensure_upstream() {
    command -v git >/dev/null 2>&1 || die "git is required"
    if [ ! -e "$SPARK_VLLM_DIR/.git" ]; then
        mkdir -p "$(dirname "$SPARK_VLLM_DIR")"
        log "cloning spark-vllm-docker into $SPARK_VLLM_DIR"
        git clone --quiet https://github.com/eugr/spark-vllm-docker.git "$SPARK_VLLM_DIR" \
            || die "could not clone spark-vllm-docker"
    fi
    if ! git -C "$SPARK_VLLM_DIR" rev-parse --verify --quiet "${SPARK_VLLM_REF}^{commit}" >/dev/null; then
        git -C "$SPARK_VLLM_DIR" fetch --quiet origin || die "git fetch failed"
    fi
    git -C "$SPARK_VLLM_DIR" rev-parse --verify --quiet "${SPARK_VLLM_REF}^{commit}" >/dev/null \
        || die "pinned upstream ref not found: $SPARK_VLLM_REF"
    if [ "$(git -C "$SPARK_VLLM_DIR" rev-parse "${SPARK_VLLM_REF}^{commit}")" != \
         "$(git -C "$SPARK_VLLM_DIR" rev-parse HEAD)" ]; then
        log "checking out spark-vllm-docker $SPARK_VLLM_REF"
        git -C "$SPARK_VLLM_DIR" checkout --quiet --detach "$SPARK_VLLM_REF" \
            || die "could not check out $SPARK_VLLM_REF"
    fi
    [ -x "$SPARK_VLLM_DIR/run-recipe.sh" ] || die "upstream run-recipe.sh is missing"
}

recipe_args() {
    local mode="$1"; shift
    local -a cmd=("$SPARK_VLLM_DIR/run-recipe.sh" "$RECIPE" --config "$ENV_FILE")
    case "$mode" in
        up)     cmd+=(--setup --daemon) ;;
        render) cmd+=(--dry-run) ;;
        setup)  cmd+=(--setup) ;;   # setup downloads image+model, does not serve
        *)      die "internal: bad recipe mode $mode" ;;
    esac
    cmd+=(--port "$PORT" --host "$HOST" --max-model-len "$MAX_MODEL_LEN" \
          --gpu-mem "$GPU_MEMORY_UTILIZATION" --name "$CONTAINER_NAME")
    [ -n "$HF_TOKEN" ] && cmd+=(-e "HF_TOKEN=$HF_TOKEN")
    cmd+=("$@")
    printf '%s\0' "${cmd[@]}"
}

run_recipe() {
    local mode="$1"; shift
    local -a cmd=()
    while IFS= read -r -d '' x; do cmd+=("$x"); done < <(recipe_args "$mode" "$@")
    log "recipe: $mode (upstream $(git -C "$SPARK_VLLM_DIR" rev-parse --short HEAD))"
    exec "${cmd[@]}"
}

container_state() {  # $1 = head|worker
    if [ "$1" = head ]; then
        docker inspect --format '{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo absent
    else
        ssh -o BatchMode=yes -o ConnectTimeout=8 "$WORKER_IP" \
            "docker inspect --format '{{.State.Status}}' $CONTAINER_NAME" 2>/dev/null || echo unreachable
    fi
}

do_stop() {
    local owned_only="${1:-}"
    if [ "$owned_only" = "--if-owned" ] && [ ! -f "$OWNED_MARKER" ]; then
        log "no kit-owned ranks to stop (marker absent)"
        return 0
    fi
    local rc=0
    log "stopping both ranks"
    docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
    ssh -o BatchMode=yes -o ConnectTimeout=8 "$WORKER_IP" \
        "docker rm -f $CONTAINER_NAME" >/dev/null 2>&1 \
        || { warn "worker $WORKER_IP did not confirm teardown"; rc=1; }
    local h w
    h="$(container_state head)"; w="$(container_state worker)"
    if [ "$h" != "absent" ] || [ "$w" != "absent" ]; then
        warn "teardown incomplete: head=$h worker=$w"
        rc=1
    fi
    [ "$rc" -eq 0 ] && { log "ranks stopped (head=absent worker=absent)"; rm -f "$OWNED_MARKER"; }
    return "$rc"
}

mem_kb() {  # $1 = head|worker; $2 = MemFree|MemAvailable
    if [ "$1" = head ]; then
        awk -v k="^$2:" '$0 ~ k {print $2}' /proc/meminfo
    else
        ssh -o BatchMode=yes -o ConnectTimeout=8 "$WORKER_IP" \
            "awk -v k='^$2:' '\$0 ~ k {print \$2}' /proc/meminfo" 2>/dev/null
    fi
}

wait_memory() {
    "$SCRIPT_DIR/scripts/wait_memory.sh" "${1:-900}"
}

do_status() {
    local h w img_ok=1
    h="$(container_state head)"; w="$(container_state worker)"
    printf 'head   %-10s %s\n' "$CONTAINER_NAME" "$h"
    printf 'worker %-10s %s\n' "$CONTAINER_NAME" "$w"
    [ "$h" = running ] && [ "$w" = running ] || img_ok=0

    local want have whave
    want="$(tr -d '[:space:]' < "$SCRIPT_DIR/receipts/expected-image-digest.txt" 2>/dev/null || true)"
    have="$(docker inspect --format '{{.Image}}' "$CONTAINER_NAME" 2>/dev/null || true)"
    whave="$(ssh -o BatchMode=yes -o ConnectTimeout=5 "$WORKER_IP" \
             "docker inspect --format '{{.Image}}' $CONTAINER_NAME" 2>/dev/null || true)"
    if [ -n "$want" ] && [ "${want#sha256:}" != "${whave#sha256:}" ]; then
        warn "worker image: ${whave:-unknown} != pinned $want"; img_ok=0
    fi
    if [ -n "$want" ] && [ -n "$have" ]; then
        [ "${want#sha256:}" = "${have#sha256:}" ] && log "image: matches pinned digest" \
            || { warn "image: running $have != pinned $want"; img_ok=0; }
    elif [ -n "$want" ] && [ "$h" = running ]; then
        warn "image: no digest reported by the container"
    fi

    local health body
    health="$(curl -s -o /dev/null -w '%{http_code}' -m 5 "http://127.0.0.1:$PORT/health" 2>/dev/null || true)"
    if [ "$health" = 200 ]; then
        body="$(curl -fsS -m 5 "http://127.0.0.1:$PORT/v1/models" 2>/dev/null || true)"
        python3 - "$body" "$MODEL_ID" "$MAX_MODEL_LEN" <<'PY' || img_ok=0
import json, sys
d = json.loads(sys.argv[1])["data"][0]
ok = d["id"] == sys.argv[2] and int(d.get("max_model_len") or 0) == int(sys.argv[3])
print(f"  model={d['id']} max_model_len={d.get('max_model_len')} "
      f"{'ok' if ok else 'MISMATCH'}")
sys.exit(0 if ok else 1)
PY
    else
        warn "health HTTP ${health:-000} on 127.0.0.1:$PORT"
        img_ok=0
    fi
    docker logs --tail 400 "$CONTAINER_NAME" 2>&1 \
        | grep -o 'GPU KV cache size: [0-9,]* tokens' | tail -1 | sed 's/^/  /' || true
    [ "$img_ok" -eq 0 ] && return 1 || return 0
}

# --- main ---------------------------------------------------------------------
action="${1:-up}"; shift || true
case "$action" in -h|--help|help) usage; exit 0 ;; esac
load_env

case "$action" in
    up)
        "$SCRIPT_DIR/scripts/preflight.sh"
        ensure_upstream
        mkdir -p "$SCRIPT_DIR/local"; : > "$OWNED_MARKER"
        run_recipe up
        ;;
    setup)
        "$SCRIPT_DIR/scripts/preflight.sh" --prepare
        ensure_upstream
        run_recipe setup
        ;;
    down)
        do_stop "${1:-}"
        ;;
    restart)
        do_stop
        wait_memory
        "$SCRIPT_DIR/scripts/preflight.sh"
        ensure_upstream
        mkdir -p "$SCRIPT_DIR/local"; : > "$OWNED_MARKER"
        run_recipe up
        ;;
    status)     do_status ;;
    logs)       case "${1:-head}" in
                    head) docker logs --tail "$TAIL" -f "$CONTAINER_NAME" ;;
                    worker) ssh "$WORKER_IP" "docker logs --tail $TAIL -f $CONTAINER_NAME" ;;
                    *) die "usage: ./launch.sh logs [head|worker]" ;;
                esac ;;
    render)     ensure_upstream; run_recipe render ;;
    preflight)  "$SCRIPT_DIR/scripts/preflight.sh" "${1:-}" ;;
    smoke)      python3 "$SCRIPT_DIR/scripts/smoke.py" --base "http://127.0.0.1:$PORT" \
                    --model "$MODEL_ID" --max-model-len "$MAX_MODEL_LEN" \
                    --container "$CONTAINER_NAME" "$@" ;;
    speed)      python3 "$SCRIPT_DIR/scripts/speed_smoke.py" --base "http://127.0.0.1:$PORT" \
                    --model "$MODEL_ID" --out "$SCRIPT_DIR/receipts" "$@" ;;
    qualify)    "$SCRIPT_DIR/scripts/qualify.sh" ;;
    *) die "unknown action '$action' (try ./launch.sh --help)" ;;
esac
