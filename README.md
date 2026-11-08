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
| Speculation | MTP-3 (`moe_backend=humming`, `attention_backend=B12X`) |
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
2. **Heavy re-quants are a different trade, not a different deployment of this
   checkpoint.** Packs around 2–3 bpw push the dense attention and MLP to 4-bit
   trellis as well and dequantize in software on the SMs; published Spark
   comparisons of that approach on this family measure roughly **+70 % cluster
   GPU power, 10–16 °C hotter GPUs, and lower prefill**. The comparison below
   deliberately covers **only deployments of `nvidia/GLM-5.3-Flash-FP4-Local`**;
   other checkpoints are listed in [docs/06](docs/06-alternatives.md).
3. **It uses the hardware you paid for.** `sm_121a` NVFP4/MXFP8 tensor cores via
   FlashInfer `b12x`, RoCEnante one-shot RoCE collectives, MTP-3 speculation —
   no software trellis, no dequant on the hot path.
4. **Capacity that matches the model.** 1M-token context with a **2.35M-token**
   FP8 KV pool: two full-context requests by pool arithmetic, four 500k requests.
   NVIDIA's own validation on this hardware is 2M tokens.
5. **Proven on this exact pair.** 2.2–2.3k tok/s cache-cold prefill and, after
   the MTP-3 window, **40.2 tok/s c1 / 79.4 c8** on a 3-rep code bench
   (+8.5 % / +8.3 % over MTP-5), draft accept rate 0.63, answers unchanged
   ([gate](docs/gates/2026-11-08-mtp3.md)).

### Same checkpoint, other kits

Seven public deployments serve **this exact checkpoint** on two Sparks. Context,
pool, seat and decode figures are each project's own; the harness note below
the table explains why they are not interchangeable.

| Deployment | Engine | Context / KV | Decode tok/s (their harness) | Seats / speculation | Operations | Licence |
|---|---|---|---|---|---|---|
| **this kit** | vLLM B12X, pinned digest | **1M / 2.35M tok** | **40.2 c1 · 79.4 c8** (3-rep code bench, MTP-3); 45 interactive peak | 4 / MTP-3 | systemd, boot-verified, watchdog, tailnet | Apache-2.0 |
| [myllmbox recipe](https://github.com/myllmbox/glm53-flash-cluster-recipe) | vLLM 0.32 + `mbx` loader | 400k / 1.15M tok | **44.9 avg c1 · 214 peak c16** | **16** / MTP 1–9 dynamic | `run.sh`, optional host tuning | MIT |
| [Flare guide](https://github.com/gpdev-Pilcothink/flare-spark) | Flare native | 1M / **3.4–4.8M tok** | **37–42** (llama-benchy tg) | **12** / MTP-5 | shell launcher, >1 h first preparation | Apache-2.0 |
| [Enntity/SparkGLM](https://github.com/Enntity/sparkglm) | Atlas | 4 × 1M profile / ~2.66M | **37.0 prose · 67.9 code** (RigMark, low effort) | 4 / DFlash2 | `start.sh`, clock-cap required | **AGPL-3.0** + **CC BY-NC-ND** drafter |
| [eugr/spark-vllm-docker](https://github.com/eugr/spark-vllm-docker) | vLLM B12X, moving nightly | 500k / 8 GiB | **37.5** (llama-benchy tg128, c1) | 4 / MTP-5 | launcher only | MIT |
| [NVIDIA DGX Spark playbook](https://github.com/NVIDIA/dgx-spark-playbooks) | same image `nightly-20261015` | 500k / recipe | **33.94** (SPEED-Bench coding) | 4 / MTP-5 | manual or launcher | NVIDIA playbook |
| [DevelopingDad recipe](https://huggingface.co/DevelopingDad/GLM-5.3-Flash-FP4-Local-DGX-Spark-Optimized) | vLLM + 4 patches | 262k / 808k tok | **31.2** (512-token request) · 58–60 decode-only | 4 / adaptive MTP | Python launcher, no boot persistence | Apache-2.0 |

Decode is not one measurement: this kit's 40.2/79.4 are a 3-rep code bench
requests at Max reasoning; myllmbox sustains 300 s streams; Flare reports
llama-benchy `tg128`/`tg1024`; SparkGLM uses RigMark at low effort; eugr's 37.5
is llama-benchy `tg128` on the same image; NVIDIA's 33.94 is SPEED-Bench;
DevelopingDad's 31.2 includes TTFT over a 512-token request, and 58–60 is
decode-only on long context.

**What this kit does better than the others on this list**

- **It is a service, not a launcher.** The only deployment here with a systemd
  unit, a two-node 90 GiB MemFree / 100 GiB MemAvailable gate, a bounded
  watchdog and a boot auto-start proven by a real two-node power cycle
  (`receipts/boot-20261108-second.txt`). The rest start a container and stop
  when the shell does.
- **Pinned and checked bytes.** Image digest, checkpoint revision, launcher
  commit and FlashInfer build are recorded and re-checked on every start;
  `preflight` fails closed on a mismatch.
- **1M context with 2.35M pooled tokens** — the largest pool among the vLLM
  recipes on this list (500k/8 GiB for eugr and the NVIDIA playbook, 262k/808k
  for the patched recipe). Flare's native cache is larger (see below).
- **The reasoning contract is asserted, not assumed.** A request without
  `reasoning_effort` renders `Reasoning Effort: Max`; `smoke` fails if the
  checkpoint default drifts.
- **Permissive and unencumbered.** Apache-2.0 kit, no AGPL engine and no
  non-commercial drafter (SparkGLM's DFlash2 is CC BY-NC-ND).
- **Least machinery to a running endpoint.** No custom loader image, no patch
  tooling, no >1 h preparation, no GPU clock cap; the scripts are stdlib-only
  and the whole path is `preflight → launch → health`.

**Where others lead**

- **Flare** — 3.4–4.8M KV tokens and 12 seats on the same pair, with comparable
  decode (37–42 tok/s in its guide), at the cost of a >1 h first preparation and
  a package on disk.
- **myllmbox** — 45 tok/s average / 214 tok/s peak at 16 streams on its own
  harness, 16 seats and a 1,836 tok/s 128k prefill, at 400k context.
- **SparkGLM** — DFlash2, TP4 chain/ring and disk/carveout KV tiering; AGPL and
  a non-commercial drafter.
- **DevelopingDad** — +23.4 % short/concurrent throughput on the same image,
  but at 262k context.
- **eugr / NVIDIA** — newer recipes and images; this kit pins instead of
  tracking.

**When not to pick it:** you need more than ~2.35M KV tokens or more than four
seats (Flare, myllmbox), you want the highest single-stream number on 400k
context (myllmbox), or you cannot spare ~166 GiB of unified memory.

Sources: [model card](https://huggingface.co/nvidia/GLM-5.3-Flash-FP4-Local),
[Flare-vs-NVFP4 Spark comparison](https://forums.developer.nvidia.com/t/spark-glm53-nvfp4-b12x-cuda-graph-dflash2-engine-for-glm-5-3-flash-on-2x-dgx-spark/386646),
[`docs/06-alternatives.md`](docs/06-alternatives.md), and this kit's receipts.

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
checkpoint, and its `glm53` recipe pins the same revision. A community guide
reports 3.4–4.8M KV tokens on the same pair — **more** than this stack's 2.35M —
with 12 seats and similar decode, but lower prefill (~1.5k vs ~2.2k tok/s) and a
first preparation that can take over an hour and leaves a ~178 GB package on
disk. It is not the deployment here because this service was already
boot-verified end to end; Flare is the first candidate for the next window. See
[`docs/06-alternatives.md`](docs/06-alternatives.md).

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
