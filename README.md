# b12x — GLM-5.3-Flash-FP4-Local on 2× DGX Spark

Deployment kit for **`nvidia/GLM-5.3-Flash-FP4-Local`** (320B MoE, 18B active,
ModelOpt FP4 QAD) on two DGX Spark nodes (GB10, 121 GiB unified memory each)
over their ConnectX-7 pair, served by **vLLM with FlashInfer's `b12x` kernels**.

`b12x` is the SM120/SM121 kernel library that lives at
[`flashinfer/experimental/b12x`](https://github.com/flashinfer-ai/flashinfer/tree/main/flashinfer/experimental/b12x)
(and at [`local-inference-lab/flashinfer`](https://github.com/local-inference-lab/flashinfer)).
Since 2026-10-07 it ships **inside FlashInfer**; the separate `b12x` wheel is
superseded. This kit runs the image that vendors that copy and pins every byte
it depends on.

## What is deployed

| Piece | Value |
|---|---|
| Checkpoint | `nvidia/GLM-5.3-Flash-FP4-Local` @ `76348ddb2be2e35e39ecfc00e75dc07703f4f3d5` |
| Image | `vllm-node-b12x` (`sha256:3b5da79c…`, pinned in `receipts/expected-image-digest.txt`) |
| Engine | vLLM `0.1.dev21830+g8244d1c44.d20261103` with `B12X` attention, `b12x` MoE/linear, `--load-format b12x` |
| Kernels | FlashInfer `0.7.1` @ `91271757`, `b12x` registry inside it |
| Parallelism | TP2 across the two Sparks, RoCEnante one-shot all-reduce/all-gather |
| Speculation | MTP-5 (`moe_backend=humming`, `attention_backend=B12X`) |
| Context | 1,000,000 tokens; FP8 pool 2,350,210 tokens (2.35× the window by pool arithmetic; two simultaneous full-context requests are not exercised) |
| Reasoning | requests that omit `reasoning_effort` render **Max** (see `docs/04-reasoning.md`) |

## Why this kit — and why `nvidia/GLM-5.3-Flash-FP4-Local`

Two Sparks hold **one** frontier-class model. On this pair the checkpoint
decision matters more than any flag: a heavy re-quantization buys fit by
degrading the dense path, while NVIDIA's FP4-Local keeps everything except the
routed experts at high precision.

1. **It is NVIDIA's own quant, not a community re-quant.** NVIDIA produced this
   checkpoint with Model Optimizer and quantization-aware distillation (QAD),
   and validated it on *2 × DGX Spark 128 GB with 2M tokens of FP8 KV cache*.
   Only the routed experts are NVFP4. Dense MLA, shared experts and the router
   stay BF16/MXFP8, and NVIDIA ships `native-QB.safetensors` in BF16
   specifically to keep `kv_b_proj` out of the FP4 path. Measured against the
   real bytes, **94.9 % of stored bytes load exactly as NVIDIA shipped them**;
   this kit never re-quantizes anything ([docs/01](docs/01-qualification.md)).
2. **Heavily quantized DeepSeek-V4.1-Flash EXL3 packs pay for their size
   elsewhere.** The 2.0–2.9 bpw packs apply lossy 4-bit trellis to the dense
   attention and MLP as well, and dequantize in software on the SMs. Published
   Spark comparisons of that approach on this model family (GLM-5.3
   EXL3-4bpw + `DENSE=q4`) measure roughly **+70 % cluster GPU power, 10–16 °C
   hotter GPUs, and lower prefill** (~1.7k vs ~2.2k tok/s) than the native-FP4
   stack, with structured-output and planning scores dropping on the dense-q4
   variants. The DeepSeek-V4.1 EXL3 packs apply the same all-linear treatment;
   their exact deltas are model-specific. For agent and tool use, that is the
   wrong trade: you spend the accuracy where it is hardest to notice until a
   tool call breaks.
3. **It uses the hardware you paid for.** `sm_121a` NVFP4/MXFP8 tensor cores via
   FlashInfer `b12x`, RoCEnante one-shot RoCE collectives, MTP-5 speculation —
   no software trellis, no dequant on the hot path.
4. **Capacity that matches the model.** 1M-token context with a **2.35M-token**
   FP8 KV pool: two full-context requests by pool arithmetic, four 500k requests.
   NVIDIA's own validation on this hardware is 2M tokens.
5. **Proven on this exact pair.** 2.2–2.3k tok/s cache-cold prefill, 27.8 tok/s
   decode at c=1 / 58.6 at c=8, MTP acceptance length 2.49–2.57, and 45 tok/s
   observed interactively in the DeepSeek Harness ([receipts](receipts/)).

| | `nvidia/GLM-5.3-Flash-FP4-Local` (this kit) | Heavy EXL3 re-quants (2.0–2.9 bpw) |
|---|---|---|
| Who quantized | NVIDIA, QAD + Model Optimizer | community re-quantization |
| 4-bit scope | routed experts only (~95 % of bytes) | experts **and** dense attention/MLP |
| Dense path | BF16 / MXFP8 / block-FP8 with F32 scales | 4-bit trellis, software dequant |
| Kernels | native Blackwell NVFP4/MXFP8 (`b12x`) | software EXL3 + Hadamard, SM-bound |
| Context / KV | 1M / 2.35M FP8 tokens | typically ≤1M and a smaller pool |
| Power & prefill | ~70 W cluster, ~2.2k tok/s | ~122 W cluster, ~1.7k tok/s (published) |

**When not to pick it:** you specifically need DeepSeek-V4.1 behaviour, you need
more than ~2.35M KV tokens, or you cannot spare ~166 GiB of unified memory. The
claim here is fidelity-per-byte and kernel efficiency on GB10 — not that one
model family is universally better than another.

Sources: [model card](https://huggingface.co/nvidia/GLM-5.3-Flash-FP4-Local),
[NVIDIA Spark EXL3-vs-NVFP4 comparison](https://forums.developer.nvidia.com/t/spark-glm53-nvfp4-b12x-cuda-graph-dflash2-engine-for-glm-5-3-flash-on-2x-dgx-spark/386646),
`docs/01-qualification.md`, and this kit's receipts.

Observed interactively: **45 tok/s** reported by the DeepSeek Harness on
2026-11-08; vLLM's own 10 s windows over that session measure p50 29.0, p90 35.1
and a 46.5 tok/s peak. The controlled cache-cold matrix lives in `receipts/` —
see [`receipts/harness-throughput-20261108.md`](receipts/harness-throughput-20261108.md).

## Quick start (on the head Spark)

```bash
git clone https://github.com/Reederey87/glm53-flash-fp4-b12x-2x-dgx-spark /home/nvidia/b12x
cd /home/nvidia/b12x
cp env.example .env                 # CLUSTER_NODES, WORKER_IP
./launch.sh preflight
./launch.sh                         # dispatch both ranks, wait for /health
./launch.sh status
./launch.sh smoke                   # models, thinking, reasoning-default, tools, prefix
./launch.sh speed                   # prefill ladder + decode c1..8 + acceptance
```

Production starts through the unit, not the script:

```bash
cp systemd/*.service systemd/*.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now vllm-b12x.service vllm-b12x-watchdog.timer vllm-b12x-tailscale.service
```

## Layout

```
launch.sh                     up/down/restart/status/logs/render/smoke/speed/qualify
env.example                   cluster, image, serving and reasoning knobs
recipes/                      the serving contract (single source of flags)
scripts/preflight.sh          read-only gate: arch, image, checkpoint, memory, peer
scripts/qualify.sh            compatibility matrix -> receipts/
scripts/smoke.py              functional acceptance over the OpenAI API
scripts/verify_reasoning.py   asserts the template's reasoning default (in-engine)
scripts/speed_smoke.py        prefill ladder + decode matrix + spec acceptance
scripts/watchdog.sh           bounded health canary (systemd timer)
scripts/tailscale_proxy.py    userspace proxy for the Tailnet endpoint
systemd/                      service + watchdog timer + tailscale unit
docs/                         architecture, qualification, runbook, gate, reasoning
spec/                         CHANGELOG + TODO (repo delivery rules)
```

## Why vLLM and not Flare

Flare (NVIDIA's `flare-local-inference`) is the other engine that targets this
checkpoint; its `glm53` recipe now pins the same revision. It is not the
deployment here: package preparation is a multi-hour, ~178 GB one-time step and
its TP2 KV capacity is roughly half of this stack's. The full comparison and the
reasons each alternative was rejected are in
[`docs/01-qualification.md`](docs/01-qualification.md).

## Credits and licenses

This kit is Apache-2.0. It integrates work by NVIDIA (checkpoint, model card,
chat template), the vLLM project, FlashInfer `b12x`, and Eugene Rakhmatulin's
MIT-licensed `spark-vllm-docker`, and it derives its watchdog/proxy from the
earlier `glm53-flash-exl3-2x-dgx-spark` kit. Per-component attribution, licenses
and exactly how each is used: [CREDITS.md](CREDITS.md), [NOTICE](NOTICE).

No weights, images, or upstream source are redistributed here.

## Operations

- **Stop:** `systemctl --user stop vllm-b12x.service` (tears down both ranks).
- **Rollback:** the deposed kit stays at `/home/nvidia/glm53-fp4-local` with its
  image and `.env`; re-enable `vllm-glm53fp4.service` after stopping this one.
- **Never** start on the teardown transient: the unit gates on ≥100 GiB
  `MemAvailable` on both nodes. GB10 has no OOM killer.
- **One treatment per window.** `docs/03-gate.md` is the pre-registered gate.
