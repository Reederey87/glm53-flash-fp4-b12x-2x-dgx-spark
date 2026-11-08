#!/usr/bin/env bash
# ============================================================================
# qualify.sh — compatibility matrix for the b12x kit (runs on the head)
# ============================================================================
# Compares the live bytes against the pinned expectations and writes a dated
# receipt. It never changes state. A non-zero exit means the deployed stack is
# not the stack this kit was qualified against.
# ============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"
RECEIPTS="$SCRIPT_DIR/receipts"
[ -f "$ENV_FILE" ] && { set -a; . "$ENV_FILE"; set +a; }
: "${CONTAINER_NAME:=vllm_node}"
: "${IMAGE_TAG:=vllm-node-b12x}"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$RECEIPTS/qualification-$STAMP.txt"
mkdir -p "$RECEIPTS"
FAIL=0
say()  { printf '%s\n' "$*" | tee -a "$OUT"; }
pass() { printf 'PASS  %s\n' "$*" | tee -a "$OUT"; }
fail() { printf 'FAIL  %s\n' "$*" | tee -a "$OUT"; FAIL=1; }

: >"$OUT"
say "b12x kit qualification — $STAMP"
say "host: $(hostname)  $(uname -m)  kernel $(uname -r)  driver $(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1)"
say ""

# --- image / engine -----------------------------------------------------------
digest="$(docker image inspect --format '{{.Id}}' "$IMAGE_TAG" 2>/dev/null || true)"
want="$(tr -d '[:space:]' < "$RECEIPTS/expected-image-digest.txt" 2>/dev/null || true)"
if [ -n "$digest" ]; then
    pass "image $IMAGE_TAG = $digest"
    if [ -n "$want" ]; then
        [ "${want#sha256:}" = "${digest#sha256:}" ] && pass "image digest matches pinned receipt" \
            || fail "image digest $digest != pinned $want"
    else
        say "INFO  no pinned digest yet (first deployment writes it)"
    fi
else
    fail "image $IMAGE_TAG missing"
fi

VLLM_VER="$(docker exec "$CONTAINER_NAME" python3 -c 'import vllm;print(vllm.__version__)' 2>/dev/null || true)"
FI_VER="$(docker exec "$CONTAINER_NAME" python3 -c 'import flashinfer.version as v;print(v.__version__, v.__git_commit__)' 2>/dev/null || true)"
TORCH_VER="$(docker exec "$CONTAINER_NAME" python3 -c 'import torch;print(torch.__version__)' 2>/dev/null || true)"
say "engine vllm=$VLLM_VER torch=$TORCH_VER"
say "kernel flashinfer=$FI_VER"
case "$VLLM_VER" in *21830*) pass "vLLM build is the pinned B12X build (dev21830)" ;; *) fail "vLLM build '$VLLM_VER' is not the pinned dev21830 build" ;; esac
case "$FI_VER" in *91271757*) pass "flashinfer is the build inside the pinned image (91271757)" ;; *) say "INFO  flashinfer commit differs from the image receipt ($FI_VER)" ;; esac

# b12x ops actually importable in this engine
OPS="$(docker exec "$CONTAINER_NAME" python3 -c 'from flashinfer.experimental import b12x; print(len(b12x.list_ops()))' 2>/dev/null || true)"
if [ -n "$OPS" ] && [ "$OPS" -gt 30 ]; then pass "b12x registry exposes $OPS ops"; else fail "b12x registry not importable (ops='$OPS')"; fi

# --- checkpoint ---------------------------------------------------------------
SNAP="$(ls -d "$HOME"/.cache/huggingface/hub/models--nvidia--GLM-5.3-Flash-FP4-Local/snapshots/*/ 2>/dev/null | head -1)"
REV="$(basename "${SNAP%/}" 2>/dev/null || true)"
if [ "$REV" = "76348ddb2be2e35e39ecfc00e75dc07703f4f3d5" ]; then
    pass "checkpoint revision $REV (pinned)"
elif [ -n "$REV" ]; then
    fail "checkpoint revision $REV != 76348ddb2be2e35e39ecfc00e75dc07703f4f3d5"
else
    fail "checkpoint snapshot not found"
fi
SHARDS="$(ls "${SNAP}"model-*.safetensors 2>/dev/null | wc -l | tr -d ' ')"
[ "$SHARDS" = "40" ] && pass "checkpoint has 40 indexed shards + native-QB" || say "INFO  checkpoint shards=$SHARDS"
QCONF="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("quantization_config",{}).get("quant_method"))' "${SNAP}config.json" 2>/dev/null || true)"
say "checkpoint quant_method=$QCONF arch=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["architectures"][0])' "${SNAP}config.json" 2>/dev/null || true)"

# --- engine surfaces used by the recipe --------------------------------------
if ! docker exec -i "$CONTAINER_NAME" python3 - <<'PY' >>"$OUT" 2>&1
import importlib
mods = ["vllm.v1.attention.backends.b12x",
        "vllm.model_executor.layers.fused_moe.b12x",
        "vllm.model_executor.kernels.linear.nvfp4.b12x"]
failed = False
for m in mods:
    try:
        importlib.import_module(m)
        print(f"PASS  import {m}")
    except Exception as e:
        failed = True
        print(f"FAIL  import {m}: {e!r}")
raise SystemExit(1 if failed else 0)
PY
then
    FAIL=1
fi
grep -q '^FAIL' "$OUT" && FAIL=1

# --- reasoned rejections (recorded, not executed) ----------------------------
say ""
say "Alternatives qualified:"
say "  Flare (nvidia/flare-local-inference): upstream ignition/recipes/glm53 declares"
say "    nvidia/GLM-5.3-Flash-FP4-Local@76348ddb (source inspection, not executed here)."
say "    Its ~178 GB package and ~1.1M-token TP2 capacity are Flare-documentation"
say "    claims, not measurements from this pair. Head free space now:"
say "    $(df -Pk / | awk 'NR==2{printf "%d GiB", $4/1048576}')."
say "  Standalone b12x package: superseded; b12x ships inside FlashInfer since"
say "    2026-10-07 and this image uses that copy."
say ""
if [ "$FAIL" -eq 0 ]; then say "VERDICT: qualified"; else say "VERDICT: NOT qualified"; fi
echo
echo "wrote $OUT"
exit "$FAIL"
