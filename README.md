# b12x — GLM-5.3-Flash on 2× DGX Spark

Serve the full **NVIDIA `GLM-5.3-Flash-FP4-Local`** 320B MoE (18B active) on **two**
DGX Spark nodes — **~43 tok/s single-stream, ~99 tok/s aggregate at 8 concurrent**,
**1,048,576-token context**, native NVIDIA Flare engine.

A pinned, receipt-backed recipe: exact checkpoint revision, audited serving parameters,
seven API smoke checks, a bounded watchdog, and a tested rollback. Clone it and reproduce
the numbers instead of re-deriving them.

## Why the NVIDIA FP4-Local quant

For a **two-Spark** cluster this is the checkpoint to use:

- **Quantization-aware distillation, not rounding.** Trained with Model Optimizer
  (`modelopt v0.47.0`, FP4 QAD 1.0) against a BF16 teacher — experts quantized to NVFP4 and
  reconstructed each forward pass, with routers, shared experts, dense MLPs and norms adapted
  to compensate. Attention and dense paths are FP8/MXFP8, which is precisely the memory trade
  that fits a 320B MoE plus a usable KV pool into two 128 GB boxes.
- **Near-lossless, with published evidence.** GPQA Diamond 92.1% → **91.3%**, ToolEvalBench
  91.9% → **92.4%** versus BF16. It is the only GLM-5.3-Flash quant for Spark that ships a
  disclosed calibration and accuracy methodology; community re-quants ship no calibration set
  or accuracy data, so there is nothing to compare against.
- **Validated here, by NVIDIA.** The card names *2× DGX Spark 128 GB with 2M tokens of FP8 KV
  cache* — the exact topology this kit targets.

(For **four** Sparks the calculus changes: memory stops being the constraint, and NVIDIA's own
author recommends the stock NVFP4 checkpoint there. This kit is deliberately a two-node recipe.)

## Measured performance

Native Flare, TP2, MTP-3, 4 slots, 200-token outputs, 3 repetitions, idle server
(`scripts/decode_bench.py`):

| Concurrency | Aggregate tok/s | Per-request tok/s |
|---|---:|---:|
| 1 | **43.04** | 43.85 |
| 2 | **83.73** | 43.02 |
| 4 | **101.10** | 27.17 |
| 8 | **99.05** | 26.11 |

For reference, the earlier vLLM/FlashInfer B12X MTP-3 deployment measured 40.2 (c1) / 79.4 (c8),
and a balanced Flare build 37.32 (c1) / 73.31 (c4) — the selected latency release is faster than
both at every concurrency. Speculative decoding is healthy throughout: **3.08 mean acceptance
length, 69.8% draft acceptance**.

Cold-prompt time to first token under a simultaneous unequal burst (one-token output budget),
balanced vs the selected **latency** scheduler:

| Prompt | Balanced | Selected | |
|---|---:|---:|---|
| 4k | 3.439 s | **1.725 s** | −49.9% |
| 8k | 8.873 s | **5.515 s** | −37.8% |
| 32k | 32.163 s | **19.938 s** | −38.0% |
| 128k | 78.529 s | 79.171 s | +0.8% |

Receipts: [`receipts/decode-flare-20261118T100526Z-postac.json`](receipts/decode-flare-20261118T100526Z-postac.json),
[`docs/50-counterbalanced-performance-repeat.md`](docs/50-counterbalanced-performance-repeat.md).

## Quick start

Requirements: 2× DGX Spark (GB10, 121 GiB unified), DGX OS 7.6.0, kernel `7.0.0-1025-nvidia`,
driver `580.178.04`, ~166 GiB of weights across the pair, and the two QSFP ports cabled.

```bash
git clone https://github.com/Reederey87/glm53-flash-fp4-b12x-2x-dgx-spark b12x-flare
cd b12x-flare
# build/export the pinned native artifact, then enable ownership
docs/07-flare-candidate.md        # preparation and export
docs/63-production-pause-checkpoint.md   # exact pins and approval record
systemctl --user enable --now b12x-flare-production.service
```

Point any OpenAI-compatible client at the head (native port **8001**, or through the tailnet proxy):

```bash
curl --fail http://127.0.0.1:8001/v1/models
curl --fail http://127.0.0.1:8001/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"nvidia/GLM-5.3-Flash-FP4-Local","messages":[{"role":"user","content":"Explain tensor parallelism briefly."}],"max_tokens":512}'
```

Model ID `nvidia/GLM-5.3-Flash-FP4-Local`; omit `reasoning_effort` for the checkpoint's **Max**
default (`low`/`high` also supported). No API key — access is bounded by SSH or the tailnet.

## What is pinned

| Parameter | Value |
|---|---|
| Parallelism / slots | TP2 / 4 |
| Speculation | Fixed MTP-3 |
| Context limit | **1,048,576** tokens per request |
| Observed KV pool | **~2.35 M** tokens, shared |
| Prefill chunk / policy | 4096 / latency |
| Memory reserve / tracing | 4 GiB per rank / off |
| Sampling defaults | temperature 1.0, top-p 0.95, effort Max |

## Operations

```bash
systemctl --user status b12x-flare-production.service
curl --fail http://127.0.0.1:8001/health
journalctl --user -u b12x-flare-production.service -n 30
```

The owner validates pins and readiness, waits for 90 GiB free / 100 GiB available per node,
starts both ranks, then runs capacity and API checks. A watchdog recovers a running-but-unhealthy
owner at most three times per six hours; a failed *startup* is retried twice by the unit itself.
A manual stop is respected.

Two hard-won operational notes:

- **Decode slows under long uptime and warm reboots** (25–40%) while clocks look normal. A full
  **AC power cycle** restores it; `reboot` does not. See [docs/65](docs/65-tps-regression-ac-cycle.md).
- **The startup KV-pool floor is tight** relative to allocator variance; flush the page cache
  before a start (`sync; echo 3 > /proc/sys/vm/drop_caches`) and never benchmark during the
  startup smoke, which requires an idle server.

Rollback: the original vLLM/FlashInfer B12X tree and image are retained on both nodes
([rollback runbook](docs/64-b12x-rollback-runbook.md)). Never run both owners.

## Layout

```
recipes/     selected release, pins and open gates
scripts/     Flare rank supervision, production owner, watchdog, smoke checks
qualification/  native patches, fixtures, frozen windows
systemd/     owner, watchdog, tailnet proxy, rollback
docs/        runbook, qualification history, performance and operational evidence
receipts/    measurements and operational evidence
```

## Credits and licenses

Integrates NVIDIA Flare, the `nvidia/GLM-5.3-Flash-FP4-Local` checkpoint and chat template,
vLLM, FlashInfer's experimental `b12x` kernels, and Eugene Rakhmatulin's `spark-vllm-docker`.
Kit code is Apache-2.0; upstream components and weights keep their own terms — see
[CREDITS.md](CREDITS.md) and [NOTICE](NOTICE). No weights, images or upstream source trees are
redistributed.

**Status:** provisional production, approved and running since 2026-11-16. Performance, capacity
and long-context gates remain open and are tracked in [docs/63](docs/63-production-pause-checkpoint.md).
