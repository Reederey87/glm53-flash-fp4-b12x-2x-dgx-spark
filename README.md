# b12x — GLM-5.3-Flash-FP4-Local on 2× DGX Spark

Deployment kit for **`nvidia/GLM-5.3-Flash-FP4-Local`** (320B MoE, 18B active,
ModelOpt FP4 QAD) on two DGX Spark nodes (GB10, 121 GiB unified memory each)
over their ConnectX-7 pair. The approved production engine is **native NVIDIA
Flare**, with the original **vLLM/FlashInfer B12X** deployment retained for rollback.

`b12x` is the SM120/SM121 kernel library that lives at
[`flashinfer/experimental/b12x`](https://github.com/flashinfer-ai/flashinfer/tree/main/flashinfer/experimental/b12x)
(and at [`local-inference-lab/flashinfer`](https://github.com/local-inference-lab/flashinfer)).
Since 2026-10-07 it ships **inside FlashInfer**; the separate `b12x` wheel is
superseded. This kit runs the image that vendors that copy and pins every byte
it depends on.

## Production status

The user approved the pinned Flare release on **2026-11-16**, with further
research paused. It is **provisional production**: seven API smoke checks pass,
but the full performance, capacity and broader quality gates remain open.
[The production checkpoint](docs/63-production-pause-checkpoint.md) records
observed activation, recovery and boot results, exact bytes, remaining work and
instructions for resuming research. [CHANGELOG.md](CHANGELOG.md) records delivery. Both-node reboot, controlled
watchdog recovery and post-boot API7/7 are verified. The current pool is
**2,347,264 tokens**; the original capacity target remains open.

The runtime is `/home/nvidia/b12x-flare`, owned by `nvidia`, under
`b12x-flare-production.service`. Its watchdog and tailnet proxy share that owner.
B12X startup is disabled; `/home/nvidia/b12x` and its original image remain the
rollback. Never start either engine directly from the Git checkout.

## Selected release

| Piece | Value |
|---|---|
| Checkpoint | `nvidia/GLM-5.3-Flash-FP4-Local` @ `76348ddb2be2e35e39ecfc00e75dc07703f4f3d5` |
| Engine | Flare `5a4e867954593b2e05bba43bc2a6eeaddca402d7`, native manifest `127424e9…`, executable `b2eb310b…` |
| Core | Native dense activations; identity `df214696…`, primary SHA `2c47847a…` |
| Serving | TP2, four slots, fixed MTP-3, prefill 4096, latency policy, trace off, reserve 4 GiB |
| Context/cache | 1M configured context; provisional startup pool floor 2,300,000 tokens; original 2,350,210 target remains open |
| Reasoning | omitted `reasoning_effort` defaults to Max; low/high/max checked at every owner startup |
| API | native `127.0.0.1:8001`; existing tailnet `:8000` endpoint |
| Rollback | B12X image `sha256:3b5da79c…`, original runtime and startup units retained |

Exact pins and explicit approval: [release decision](recipes/flare-production-decision-20261116.json).
Use the [current runbook](docs/02-runbook.md) for start, stop and rollback.
The comparisons below describe the original B12X recipe and published alternatives;
they are historical context, not a measured advantage of this Flare release.

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

## Operate the installed release

As `nvidia` on the head Spark:

```bash
cd /home/nvidia/b12x-flare
systemctl --user status b12x-flare-production.service
curl --fail http://127.0.0.1:8001/health
journalctl --user -u b12x-flare-production.service -n 30
```

Use [the current runbook](docs/02-runbook.md) for start/stop, maintenance and
rollback. `launch.sh` remains the original B12X launcher; it does not select the
Flare production owner. Do not enable all unit files together.

For a fresh installation, keep the Git staging tree separate from the runtime.
The [preparation workflow](docs/07-flare-candidate.md) explains building/exporting;
apply the exact artifact, wrapper revisions and production decision in
[docs/63](docs/63-production-pause-checkpoint.md) before enabling ownership.
Historical candidate defaults and experiment controllers are not a production
installer. No build, export or new experiment is required to use the current
installed release.

## Layout

```
recipes/flare-glm53.json            pinned checkpoint, engine and core settings
recipes/flare-production-*.json    explicit selected release and open gates
scripts/flare_production.*         pinned owner, readiness and capacity checks
scripts/flare_watchdog.py          bounded persistent recovery
scripts/flare_run.*                native rank supervision; deployed revision pinned
scripts/flare_smoke.py             seven API checks, including default reasoning
scripts/flare_*.py                 preparation and qualification tools
qualification/                    native patches, fixtures and frozen windows
systemd/b12x-flare-*               production owner, watchdog, proxy and rollback
launch.sh                         retained original B12X deployment launcher
docs/                             current runbook and historical qualification
receipts/                         retained measurements and operational evidence
CHANGELOG.md                      public release record
spec/                             ignored canonical TODO and PR changelog
```

## Flare qualification and research checkpoint

The original interleaved scheduler delayed early concurrent prompt responses.
The selected latency scheduler has native tracing evidence, but the final mixed
ABBA still contains ten unresolved adverse median points out of eighty. No full
84-row performance-preservation pass is claimed. See the [retained ABBA result](docs/50-counterbalanced-performance-repeat.md)
and the definitive links in [docs/63](docs/63-production-pause-checkpoint.md).

Completed numerical evidence includes component/state, expert, MLA, representative
layer, 45-layer target, vocabulary and full MTP replay checks with original bounds.
These do not establish independent full-model or exported-core equivalence.
The public generation comparison stopped on the research pause at 100 baseline
and 86 candidate responses; it is incomplete. Warmup and fractional-reserve
experiments are staged/local proposals, not production settings.

Historical trials, failures and receipts remain in `docs/` and
`receipts/flare-qualification-20261115/`. Old controllers assume B12X owns
production and must be adapted to this Flare rollback checkpoint before reuse.

## Credits and licenses

This kit is Apache-2.0. It integrates work by NVIDIA (Flare, checkpoint, model card,
chat template), the vLLM project, FlashInfer `b12x`, and Eugene Rakhmatulin's
MIT-licensed `spark-vllm-docker`, and it derives its watchdog/proxy from the
earlier `glm53-flash-exl3-2x-dgx-spark` kit. Per-component attribution, licenses
and exactly how each is used: [CREDITS.md](CREDITS.md), [NOTICE](NOTICE).

No weights, images, or full upstream source trees are redistributed here.

## Operations

As `nvidia` on spark1:

```bash
systemctl --user status b12x-flare-production.service
systemctl --user stop b12x-flare-production.service
systemctl --user start b12x-flare-production.service b12x-flare-tailscale.service
```

The owner tears down both ranks, verifies exact pins, waits for the peer and
90GiB free / 100GiB available on both nodes, then requires health, capacity and
seven API checks. A manual stop is respected by the watchdog. See the
[runbook](docs/02-runbook.md) for maintenance, recovery and B12X rollback.
No driver or kernel upgrade is part of this release.
