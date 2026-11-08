#!/usr/bin/env bash
# ============================================================================
# preflight.sh — read-only gate for the b12x kit
# ============================================================================
# Default mode fails closed on anything that would make a start impossible or
# unsafe on GB10 unified memory. `--prepare` skips the serving-only checks
# (memory, port) so image/checkpoint staging can run while a model is resident.
# ============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"
RECEIPTS="$SCRIPT_DIR/receipts"
CHECKPOINT_REV="76348ddb2be2e35e39ecfc00e75dc07703f4f3d5"
MODE="${1:-}"

[ -f "$ENV_FILE" ] || { echo "missing $ENV_FILE" >&2; exit 1; }
set -a; . "$ENV_FILE"; set +a
: "${HEAD_IP:=}"
: "${WORKER_IP:=}"
: "${CONTAINER_NAME:=vllm_node}"
: "${PORT:=8000}"
: "${IMAGE_TAG:=vllm-node-b12x}"

FAIL=0
ok()   { printf '  \033[1;32mok\033[0m   %s\n' "$*"; }
warn() { printf '  \033[1;33mwarn\033[0m %s\n' "$*" >&2; }
fail() { printf '  \033[1;31mFAIL\033[0m %s\n' "$*" >&2; FAIL=1; }

MIN_FREE_KB=$((90 * 1024 * 1024))     # 90 GiB MemFree  (CUDA-free excludes cache)
MIN_AVAIL_KB=$((100 * 1024 * 1024))   # 100 GiB MemAvailable

echo "[b12x] preflight (${MODE:-serve})"

# --- host ---------------------------------------------------------------------
case "$(uname -m)" in
    aarch64|arm64) ok "architecture $(uname -m)" ;;
    *) fail "architecture $(uname -m); DGX Spark is aarch64" ;;
esac

if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    ok "docker $(docker version --format '{{.Server.Version}}' 2>/dev/null || echo '?')"
else
    fail "docker is not installed or the daemon is not reachable"
fi

if nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | grep -qi GB10; then
    ok "NVIDIA GB10 visible"
else
    fail "NVIDIA GB10 not visible through nvidia-smi"
fi

mfk="$(cat /proc/sys/vm/min_free_kbytes 2>/dev/null || echo 0)"
[ "$mfk" -ge 1048576 ] && ok "vm.min_free_kbytes=$mfk" \
    || warn "vm.min_free_kbytes=$mfk (pair is normally pinned to 1048576)"

[ -e /sys/class/infiniband/rocep1s0f1 ] && ok "RoCE device rocep1s0f1 present" \
    || fail "RoCE device rocep1s0f1 missing"

# --- image --------------------------------------------------------------------
if docker image inspect "$IMAGE_TAG" >/dev/null 2>&1; then
    have="$(docker image inspect --format '{{.Id}}' "$IMAGE_TAG")"
    want="$(tr -d '[:space:]' < "$RECEIPTS/expected-image-digest.txt" 2>/dev/null || true)"
    if [ -n "$want" ]; then
        [ "${want#sha256:}" = "${have#sha256:}" ] \
            && ok "head image matches pinned digest $have" \
            || fail "head image $have != pinned $want"
    else
        warn "head image $IMAGE_TAG present ($have); no pinned digest yet"
    fi
else
    [ "$MODE" = "--prepare" ] && warn "head image missing (setup will fetch/build it)" \
        || fail "image $IMAGE_TAG missing on the head (PULL_IMAGE=0)"
fi

# --- checkpoint ---------------------------------------------------------------
HF="${HF_HOME:-$HOME/.cache/huggingface}"
SNAP="$HF/hub/models--nvidia--GLM-5.3-Flash-FP4-Local/snapshots/$CHECKPOINT_REV"
checkpoint_ok() {  # $1 = label
    if [ ! -d "$SNAP" ]; then
        [ "$MODE" = "--prepare" ] && { warn "$1: snapshot missing (setup will fetch it)"; return; }
        fail "$1: snapshot $CHECKPOINT_REV missing"; return
    fi
    if [ ! -f "$SNAP/model.safetensors.index.json" ]; then
        fail "$1: model.safetensors.index.json missing"; return
    fi
    local missing
    missing="$(python3 - "$SNAP" <<'PY'
import json, os, sys
snap = sys.argv[1]
idx = json.load(open(os.path.join(snap, "model.safetensors.index.json")))
files = sorted(set(idx.get("weight_map", {}).values()))
bad = [f for f in files if not os.path.exists(os.path.join(snap, f))]
print(len(bad))
PY
)"
    if [ "${missing:-1}" = "0" ]; then
        ok "$1: revision $CHECKPOINT_REV complete ($(ls "$SNAP"/model-*.safetensors | wc -l | tr -d ' ') shards)"
    else
        fail "$1: $missing indexed shard(s) missing in $CHECKPOINT_REV"
    fi
    [ -f "$SNAP/chat_template.jinja" ] && ok "$1: chat template present" \
        || warn "$1: chat_template.jinja absent"
}
checkpoint_ok head

# --- memory -------------------------------------------------------------------
if [ "$MODE" != "--prepare" ]; then
    free="$(awk '/^MemFree:/ {print $2}' /proc/meminfo)"
    avail="$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)"
    if [ "${free:-0}" -ge "$MIN_FREE_KB" ] && [ "${avail:-0}" -ge "$MIN_AVAIL_KB" ]; then
        ok "head MemFree $((free / 1048576)) GiB / MemAvailable $((avail / 1048576)) GiB"
    else
        fail "head MemFree $(( ${free:-0} / 1048576 )) GiB / MemAvailable $(( ${avail:-0} / 1048576 )) GiB (need 90/100); stop the resident model"
    fi
fi

if [ "$MODE" != "--prepare" ] && curl -fsS --max-time 3 "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
    fail "something answers on 127.0.0.1:$PORT/health; stop it before starting"
fi

# --- worker -------------------------------------------------------------------
if [ -z "$WORKER_IP" ]; then
    fail "WORKER_IP is empty; this recipe is cluster_only"
else
    if ssh -o BatchMode=yes -o ConnectTimeout=8 "$WORKER_IP" true >/dev/null 2>&1; then
        ok "passwordless ssh to worker $WORKER_IP"
        if [ "$MODE" != "--prepare" ]; then
            wf="$(ssh -o BatchMode=yes -o ConnectTimeout=8 "$WORKER_IP" "awk '/^MemFree:/ {print \$2}' /proc/meminfo" 2>/dev/null || echo 0)"
            wa="$(ssh -o BatchMode=yes -o ConnectTimeout=8 "$WORKER_IP" "awk '/^MemAvailable:/ {print \$2}' /proc/meminfo" 2>/dev/null || echo 0)"
            if [ "${wf:-0}" -ge "$MIN_FREE_KB" ] && [ "${wa:-0}" -ge "$MIN_AVAIL_KB" ]; then
                ok "worker MemFree $((wf / 1048576)) GiB / MemAvailable $((wa / 1048576)) GiB"
            else
                fail "worker MemFree $(( ${wf:-0} / 1048576 )) GiB / MemAvailable $(( ${wa:-0} / 1048576 )) GiB (need 90/100)"
            fi
        fi
        wmfk="$(ssh -o BatchMode=yes -o ConnectTimeout=8 "$WORKER_IP" "cat /proc/sys/vm/min_free_kbytes" 2>/dev/null || echo 0)"
        [ "$wmfk" = "$mfk" ] && ok "vm.min_free_kbytes symmetric ($mfk)" \
            || fail "vm.min_free_kbytes head=$mfk worker=$wmfk (change both or neither)"
        if ssh -o BatchMode=yes -o ConnectTimeout=8 "$WORKER_IP" "docker image inspect $IMAGE_TAG" >/dev/null 2>&1; then
            whave="$(ssh -o BatchMode=yes -o ConnectTimeout=8 "$WORKER_IP" "docker image inspect --format '{{.Id}}' $IMAGE_TAG" 2>/dev/null || true)"
            wwant="$(tr -d '[:space:]' < "$RECEIPTS/expected-image-digest.txt" 2>/dev/null || true)"
            if [ -n "$wwant" ] && [ "${wwant#sha256:}" != "${whave#sha256:}" ]; then
                fail "worker image $whave != pinned $wwant"
            else
                ok "worker image matches pinned digest"
            fi
        else
            [ "$MODE" = "--prepare" ] && warn "worker image missing (setup will copy it)" \
                || fail "worker image $IMAGE_TAG missing"
        fi
        wsnap="\$HOME/.cache/huggingface/hub/models--nvidia--GLM-5.3-Flash-FP4-Local/snapshots/$CHECKPOINT_REV"
        if ! ssh -o BatchMode=yes -o ConnectTimeout=8 "$WORKER_IP" \
              "test -f $wsnap/model.safetensors.index.json && test -f $wsnap/chat_template.jinja"; then
            [ "$MODE" = "--prepare" ] && warn "worker checkpoint missing (setup will copy it)" \
                || fail "worker checkpoint revision $CHECKPOINT_REV incomplete"
        else
            wbad="$(ssh -o BatchMode=yes -o ConnectTimeout=8 "$WORKER_IP" \
                "python3 - '$wsnap' <<'PY'
import json, os, sys
snap = sys.argv[1]
idx = json.load(open(os.path.join(snap, 'model.safetensors.index.json')))
files = sorted(set(idx.get('weight_map', {}).values()))
print(sum(0 if os.path.exists(os.path.join(snap, f)) else 1 for f in files))
PY" 2>/dev/null || echo 1)"
            [ "${wbad:-1}" = "0" ] && ok "worker checkpoint revision complete" \
                || fail "worker checkpoint: $wbad indexed shard(s) missing"
        fi
    else
        fail "cannot ssh to worker $WORKER_IP"
    fi
fi

if [ "$FAIL" -ne 0 ]; then
    echo "[b12x] preflight failed" >&2
    exit 1
fi
echo "[b12x] preflight passed"
