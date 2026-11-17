# b12x — GLM-5.3-Flash-FP4-Local on 2× DGX Spark

Deployment kit for **`nvidia/GLM-5.3-Flash-FP4-Local`** on two NVIDIA DGX Spark
nodes (GB10, 121 GiB unified memory each). The installed production engine is
**native NVIDIA Flare**, with the original **vLLM/FlashInfer B12X** deployment
retained for rollback. The repository name reflects that original deployment;
`launch.sh` still launches B12X, not Flare.

## Production status

The pinned Flare release was approved and merged in [PR #2](https://github.com/Reederey87/glm53-flash-fp4-b12x-2x-dgx-spark/pull/2)
on **2026-11-16**. Both ranks started automatically after a controlled two-node
reboot; watchdog recovery, generation and all seven API smoke checks passed.
Further research is paused. This is **provisional production**: the full
performance, capacity and broader quality gates remain open.

The runtime is `/home/nvidia/b12x-flare`, owned by `nvidia`, under
`b12x-flare-production.service`. Its watchdog and tailnet proxy are enabled.
B12X startup is disabled; `/home/nvidia/b12x` and its original image remain the
rollback. [The production checkpoint](docs/63-production-pause-checkpoint.md)
records exact bytes, activation/recovery/reboot receipts and remaining work.

## Connect a client

For the existing Mac SSH tunnel, use these provider settings:

| Setting | Value |
|---|---|
| Base URL | **`http://127.0.0.1:18899/v1`** |
| API protocol | **OpenAI Chat Completions** |
| Model ID | **`nvidia/GLM-5.3-Flash-FP4-Local`** |
| API key | Leave blank; use `local` if the client requires a nonempty value |
| Retry policy | Default / transient errors |

Fetch the available models after changing the URL. On this Mac, the older
`127.0.0.1:18000` tunnel forwards to head port 8000; native Flare listens on
head loopback **8001**. The existing 18899 tunnel targets that working port.
Health, model discovery and a chat completion through it were verified.

On another client, create a tunnel with a free local port and keep it running
while using the API. This example uses 18899; do not start a second tunnel if
that port already has the working forward:

```bash
ssh -N -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
  -L 127.0.0.1:18899:127.0.0.1:8001 nvidia@spark-a183.local
```

The SSH host must resolve and accept your configured key. Then, in another terminal:

```bash
curl --fail http://127.0.0.1:18899/v1/models
curl --fail http://127.0.0.1:18899/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"nvidia/GLM-5.3-Flash-FP4-Local","messages":[{"role":"user","content":"Explain tensor parallelism briefly."}],"reasoning_effort":"low","max_tokens":512,"temperature":1.0,"top_p":0.95}'
```

Omit `reasoning_effort` for the checkpoint's **Max** default; `low` and `high`
are also supported. Allow enough output tokens for reasoning and the answer.
Temperature zero is clamped to the native sampler's advertised range; it does
**not** select greedy decoding. Inspect `/v1/models` for the sampling contract.

On the head itself, use `http://127.0.0.1:8001/v1`. The installed tailnet proxy
serves `http://100.125.23.98:8000/v1`; a client needs a working tailnet route.
Direct access from a remote tailnet client remains an open verification item.
There is no API-key authentication in this release: access is bounded by SSH
or the tailnet, and entering `local` does not add authentication.

## Selected release and serving parameters

| Parameter | Installed value |
|---|---|
| Checkpoint revision | `76348ddb2be2e35e39ecfc00e75dc07703f4f3d5` |
| Flare source | `5a4e867954593b2e05bba43bc2a6eeaddca402d7` |
| Native artifact / executable | Manifest `127424e9…` / SHA `b2eb310b…` |
| Exported core | Native dense activations; identity `df214696…`, primary SHA `2c47847a…` |
| Parallelism / request slots | TP2 / **4** slots; context parallelism off |
| Speculation | Fixed **MTP-3** |
| Prefill / scheduler | **4096-token** chunks / selected latency policy |
| Context limit | **1,048,576 tokens** per request, shared by prompt and output |
| Observed post-boot KV pool | **2,347,264 tokens** shared across requests and retained prefixes |
| Capacity gate | Provisional startup floor **2,300,000**; original **2,350,210** target still open |
| Memory reserve / tracing | **4 GiB per rank** / native tracing off |
| Sampling / reasoning defaults | Temperature **1.0**, top-p **0.95**, omitted effort = **Max** |
| Modalities | **Text only** in this Flare export |
| Rollback image | B12X `sha256:3b5da79c…`, retained on both nodes |

Pool allocation varies with startup memory. Do not multiply pooled tokens by
TP ranks or interpret four slots as four simultaneous full-context requests.
Configured context and pool size do not establish long-context correctness.
Exact pins, installed wrapper revisions and approval are in the
[release decision](recipes/flare-production-decision-20261116.json) and
[production checkpoint](docs/63-production-pause-checkpoint.md).

## Why this kit

- **A defined checkpoint and runtime.** NVIDIA's model card describes a 320B MoE
  with 18B active parameters, quantized with Model Optimizer and
  quantization-aware distillation. It uses approximately 166 GiB for weights
  across the pair; NVIDIA reports vLLM validation on two Sparks with 2M FP8 KV
  tokens. That vendor validation does not qualify this Flare export. The kit
  pins the source checkpoint, prepared core, executable and deployed wrappers.
  [Model card](https://huggingface.co/nvidia/GLM-5.3-Flash-FP4-Local).
- **Recorded two-node operations.** The owner checks identities and readiness,
  waits for 90 GiB free / 100 GiB available on each idle node, starts both
  ranks, and requires capacity and API checks. Controlled watchdog recovery
  and boot startup have retained receipts; a pinned B12X rollback survives.
- **An explicit client contract.** Seven smoke checks cover model/context
  discovery, sampler behavior, reasoning defaults, tools, structured output,
  prefix reuse and cancellation/recovery. These establish integration behavior,
  not general answer quality.
- **Reviewable performance evidence.** Prompt service, output delivery gaps,
  acceptance and failures remain in the repository. Improvements and unresolved
  regressions are reported together, with a checkpoint for resuming research.

The tradeoffs are real: preparing Flare requires a native build/export, this
release offers four slots and a smaller observed pool than the public Flare
guide below, and multimodal input is not enabled. Choose this kit for its pinned
operational setup and retained evidence; it has no established speed lead over
other deployments. Kit code is Apache-2.0; upstream components and model weights
retain their own terms ([CREDITS](CREDITS.md), [NOTICE](NOTICE)).

## Measured performance of the selected Flare artifact

The strongest retained comparison uses the **same native artifact and core**,
changing only balanced versus latency scheduling. Four fresh starts ran in
balanced/latency/latency/balanced order, with three repetitions per start and
**348 measured requests**. Both policies used TP2, four slots, MTP-3, chunk
4096, reserve 4 GiB, tracing off and Max reasoning.

For a simultaneous unequal burst, with a one-token output budget per request,
the combined median time to first token (TTFT) was:

| Cold prompt | Balanced policy | Selected latency policy | Change |
|---|---:|---:|---:|
| 128k (131,072 tokens) | 78.529 s | 79.171 s | +0.82% |
| 32k (32,768 tokens) | 32.163 s | 19.938 s | −38.01% |
| 8k (8,192 tokens) | 8.873 s | 5.515 s | −37.84% |
| 4k (4,096 tokens) | 3.439 s | 1.725 s | −49.85% |
| Whole burst completion | 78.552 s | 79.191 s | +0.81% |

Earlier small-prompt responses improved substantially; total burst duration
barely changed. In the separate concurrent fixed-256-output suite, median
cohort duration was **115.258 → 114.549 s**, mean acceptance length
**1.733 → 1.777**, and draft acceptance rate **24.52% → 26.03%**.
These are workload-specific measurements, not a single-stream decode benchmark.

The complete result remains **70/80 points without an adverse median over 2%,
10 unresolved adverse medians, zero separated regressions over 2% in either
order pair**. For example, one overlapping decoder's amortized rate fell
**4.10%**, and the fixed-output 8k request's elapsed time rose **10.52%**.
Overlapping ranges do not establish equivalence: **the registered gate did not
pass**. Six observations per request role come from only two starts per policy.
See the [complete result](docs/50-counterbalanced-performance-repeat.md) and
[machine-readable comparison](receipts/flare-qualification-20261115/performance-abba-comparison.json).

For historical context, an earlier **balanced Flare** build measured aggregate
code rates of **37.32 tok/s at c1** and **73.31 at c4**, using 200-token outputs
and including startup/queueing; its cold c1 128k TTFT was **58.34 s**.
It failed concurrent-prefill gates. Those results and the original B12X
**40.2 c1 / 79.4 c8** MTP-3 figures are **not measurements of the selected
latency release**. The full matched 84-row comparison against B12X remains open.
[Historical Flare result](docs/13-flare-native-serving-result.md),
[B12X MTP-3 gate](docs/gates/2026-11-08-mtp3.md).

## Same checkpoint on two Sparks

Primary sources reviewed with Exa MCP on **2026-11-16**. Each row describes its
publisher's configuration and test; these are **not a speed ranking**. NVFP4
and EXL3 checkpoints with different weight quantization are outside this table.

| Deployment | Engine / capacity / concurrency | Published performance and method |
|---|---|---|
| **This kit, selected release** | Flare; 1,048,576 context; observed 2,347,264 pooled tokens; 4 slots; MTP-3 | Selected-artifact scheduler comparison above; full cross-engine performance pass still open |
| [Public Flare guide](https://github.com/gpdev-Pilcothink/flare-spark/blob/main/Guide/GLM53-Flash.md) | Flare; 1,048,576 context; observed 3,439,616 pooled tokens; 12 slots; MTP-5, chunk 8192 | llama-benchy: **38.21 ± 0.18 tok/s tg128**, **37.46 ± 3.11 tg1024** |
| [myllmbox](https://github.com/myllmbox/glm53-flash-cluster-recipe) | vLLM + custom loader; 400k context; 1,145,238 pooled tokens; 16 streams; dynamic MTP up to 9 | Thinking-on pasture c1: **44.9 tok/s average**; **214.2 aggregate c16 peak**, a separate peak statistic; sustained-stream harness |
| [SparkGLM](https://github.com/Enntity/sparkglm) | Atlas engine with DFlash2; use its TP2 profile | 2026-11-11 RigMark, 4096 output tokens, low effort: **66.0 code / 38.1 prose / 89.0 structured tok/s**; cold 16k prefill **2865 tok/s** |
| [tsarihan 1M playbook](https://github.com/tsarihan/glm-5.3-flash-fp4-local-1m-2x-dgx-spark-playbook) | vLLM B12X; 1,048,576 context; 8 sequences; adaptive MTP up to 5; multimodal pool 1,307,683 tokens | **~33 tok/s c1**; 990,010-token prompt **587.5 s cold TTFT / 7.7 s repeated-prefix TTFT**, two needles found on both passes |
| [NVIDIA recipe](https://nvidia.github.io/local-ai-inference-recipes/hardware/dgx-spark-2gpu/index.html?backend=vllm&memory=128&memoryConfig=128&model=z-ai%2Fglm-5.3-flash&os=linux&precision=fp4-local) | Official two-Spark vLLM FP4-Local recipe | **33.94 tok/s**, SPEED-Bench qualitative coding |
| [DevelopingDad](https://huggingface.co/DevelopingDad/GLM-5.3-Flash-FP4-Local-DGX-Spark-Optimized) | vLLM + four patches; 262,144 context; 808,020 pooled tokens; 4 slots; adaptive MTP | **+23.43% short/concurrent throughput against its own baseline**; not a gain measured against this Flare release |

Context limit, pooled cache capacity and request slots measure different things.
Likewise, per-stream and aggregate rates, peaks and averages, cold and cached
prefill, output budgets and reasoning settings are not interchangeable. Sharing
checkpoint weights does not imply identical arithmetic, sampler behavior or
speculative decoding. A fair comparison needs matched requests and quality/state
checks. [The detailed survey](docs/06-alternatives.md) records tradeoffs and
possible future experiments; none changes the installed release.

## Operate the installed release

As `nvidia` on the head Spark:

```bash
cd /home/nvidia/b12x-flare
systemctl --user status b12x-flare-production.service
curl --fail http://127.0.0.1:8001/health
journalctl --user -u b12x-flare-production.service -n 30
```

Use [the current runbook](docs/02-runbook.md) for start/stop, maintenance and
rollback. A manual stop is respected by the watchdog. Never deploy from the Git
checkout or enable B12X and Flare owners together. No driver or kernel upgrade
is part of this release.

For a fresh installation, keep staging separate from the runtime. The
[preparation workflow](docs/07-flare-candidate.md) explains building/exporting;
apply the exact artifact, wrapper revisions and production decision in
[docs/63](docs/63-production-pause-checkpoint.md) before enabling ownership.
Historical candidate defaults and experiment controllers are not a production
installer. No build or export is required to use the installed release.

## Research checkpoint

Research is paused. Remaining work includes mixed/long-output performance,
the original capacity target, independent full-model/exported-core equivalence,
and long-context/state qualification. Component, expert, MLA, representative
layer, 45-layer target, vocabulary and full MTP replay evidence is retained;
it does not establish whole-model correctness. The public generation comparison
stopped at 100 baseline and 86 candidate responses and is incomplete.

Warmup and fractional-reserve experiments are proposals, not production settings.
Before resuming, use [docs/63](docs/63-production-pause-checkpoint.md); old
controllers assume B12X owns production and need adaptation to the Flare checkpoint.

## Layout

```
recipes/flare-production-*.json    selected release, pins and open gates
scripts/flare_production.*         production owner and readiness checks
scripts/flare_watchdog.py          bounded persistent recovery
scripts/flare_run.*                rank supervision; deployed revision pinned
scripts/flare_smoke.py             seven API checks
scripts/flare_*.py                 preparation and qualification tools
qualification/                    native patches, fixtures and frozen windows
systemd/b12x-flare-*               owner, watchdog, proxy and rollback
launch.sh                         original B12X deployment launcher
docs/                             current runbook and historical qualification
receipts/                         measurements and operational evidence
CHANGELOG.md                      public release record
spec/                             ignored canonical TODO and PR changelog
```

## Credits and licenses

This kit integrates NVIDIA Flare, the checkpoint and chat template, vLLM,
FlashInfer's experimental `b12x` kernels, and Eugene Rakhmatulin's
`spark-vllm-docker`. Watchdog/proxy work derives from the earlier EXL3 kit.
See [CREDITS.md](CREDITS.md) and [NOTICE](NOTICE) for component attribution and
licenses. No weights, images or full upstream source trees are redistributed.
