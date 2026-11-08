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
