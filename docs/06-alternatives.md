# Same-checkpoint alternatives on two DGX Sparks

Updated **2026-11-16** using Exa MCP searches and primary model cards, guides
and repository READMEs. This survey covers deployments of
`nvidia/GLM-5.3-Flash-FP4-Local` on two GB10 Sparks. Other NVFP4, EXL3 and
low-bit checkpoints have different weight representations and are excluded.
The same model family name alone is not sufficient for inclusion.

Current production is the selected native **Flare** artifact, not this kit's
original vLLM B12X image. [README](../README.md) gives connection settings,
serving parameters and the comparison table; [docs/63](63-production-pause-checkpoint.md)
is the operational checkpoint. Research remains paused.

## Evidence and tradeoffs

### This kit: pinned Flare operations

The installed release has TP2, four slots, fixed MTP-3, 4096-token prefill chunks,
latency scheduling, 1,048,576 configured context and an observed post-boot
2,347,264-token pool. It is text only. Exact native/core/wrapper identities,
two-node startup, API7/7, watchdog recovery, reboot and retained B12X rollback
have recorded evidence.

The selected artifact's counterbalanced scheduler comparison includes 348
measured requests. In the simultaneous 128k/32k/8k/4k one-output-token burst,
latency-policy median TTFT is 79.171/19.938/5.515/1.725 seconds. Balanced-policy
medians are 78.529/32.163/8.873/3.439 seconds. Whole-burst duration changes
78.552→79.191 seconds. Shorter requests finish prefill earlier without a
corresponding aggregate throughput gain.

The full result retains **10 unresolved adverse medians out of 80 metrics**;
the original 2% performance gate did not pass. A full matched 84-row B12X versus
selected-Flare comparison is outstanding. Historical balanced-Flare decode and
B12X MTP-3 numbers are labeled separately in the README and must not be presented
as the current release's benchmark. [Complete ABBA result](50-counterbalanced-performance-repeat.md),
[raw comparison](../receipts/flare-qualification-20261115/performance-abba-comparison.json).

This kit offers a reproducible operational checkpoint and an explicit record
of incomplete qualification. It does not claim exclusive systemd support,
minimal preparation, the largest cache or the fastest serving performance.

### Public Flare guide: more request slots and cache

The [GLM53-Flash guide](https://github.com/gpdev-Pilcothink/flare-spark/blob/main/Guide/GLM53-Flash.md)
uses the same source checkpoint with native Flare, 1,048,576 context, 12 slots,
MTP-5 and 8192-token prefill chunks. Its illustrated 11.8 GiB cache allocation
reports **3,439,616 pooled tokens**. Published llama-benchy decode is
**38.21 ± 0.18 tok/s for tg128** and **37.46 ± 3.11 for tg1024**.

This is a useful capacity/concurrency reference, not proof that changing this
kit to 12 slots will preserve latency, state correctness or memory headroom.
Native preparation, exported settings and runtime allocations must be compared;
12 slots do not imply 12 simultaneous full-context conversations. The guide's
allocation is an observation, not a guaranteed pool size for every startup.

### myllmbox: sustained multi-stream workloads

The [cluster recipe](https://github.com/myllmbox/glm53-flash-cluster-recipe)
uses vLLM with its custom loader, 400k context, **1,145,238 pooled tokens**,
16 streams and dynamic MTP up to nine drafts. It reports **44.9 tok/s average**
for a thinking-on pasture request at c1 and **214.2 tok/s aggregate peak** at
c16, using sustained-stream measurements. These are different statistics from
different workload cells; the latter is neither a c1 rate nor a sustained mean.
Its published 128k prefill rate is **1836 tok/s**.

The relevant trade is a larger admitted stream count with a smaller configured
context and pool. Its results motivate matched concurrency measurements; they
do not establish a speed lead over this kit under the same workload.

### SparkGLM: separate engine and drafter

[SparkGLM](https://github.com/Enntity/sparkglm) uses the Atlas engine and DFlash2.
Its 2026-11-11 v0.3.3 RigMark result, at 4096 output tokens and low reasoning
effort, reports **66.0 code / 38.1 prose / 89.0 structured tok/s**, with
**2865 tok/s cold 16k prefill**. Use the two-node TP2 figures; TP4 chain/ring
results require additional hardware and are outside this comparison.

The engine and additional drafter change the execution path. Compare sampling,
quality and actual output-token counts as well as speed, and inspect both engine
and drafter licensing before adoption. These low-effort results cannot rank
against this kit's Max-reasoning, different-output-budget measurements.

### tsarihan: documented 1M context and repeated-prefix behavior

The [1M playbook](https://github.com/tsarihan/glm-5.3-flash-fp4-local-1m-2x-dgx-spark-playbook)
uses the vLLM B12X fork, 1,048,576 context, eight sequences, 8192-token chunks
and adaptive MTP up to five drafts. It reports **~33 tok/s single-stream decode**
and **1685–2140 tok/s prefill** on its long prompts. The multimodal profile
reports **1,307,683 pooled tokens**; its separate text-only configuration reports
**1,327,926**. Those allocations belong to different settings.

A **990,010-token** prompt takes **587.5 s cold TTFT** and **7.7 s** on a repeated
prefix; both needles were found on both passes. This is useful long-context and
cache-reentry evidence for that deployment, not a full-context correctness
result for Flare. It also exposes image/video capability absent from this kit's
selected text-only export.

### NVIDIA reference recipe

The [official two-Spark FP4-Local recipe](https://nvidia.github.io/local-ai-inference-recipes/hardware/dgx-spark-2gpu/index.html?backend=vllm&memory=128&memoryConfig=128&model=z-ai%2Fglm-5.3-flash&os=linux&precision=fp4-local)
reports **33.94 tok/s** on SPEED-Bench qualitative coding. Preserve that workload
label when citing the figure; it is not a matched measurement against this kit.
The [model card](https://huggingface.co/nvidia/GLM-5.3-Flash-FP4-Local) reports
vLLM validation on two Sparks with 2M FP8 KV tokens and links compatible serving
instructions. [eugr/spark-vllm-docker](https://github.com/eugr/spark-vllm-docker)
is a reference launcher used by this ecosystem and credited in this kit.

The checkpoint uses mixed precision and compressed quantization scales;
checkpoint compatibility must be checked against the pinned runtime. NVIDIA's
vLLM validation does not establish equivalence of another engine's exported core.

### DevelopingDad: a bounded patch comparison

The [optimized recipe](https://huggingface.co/DevelopingDad/GLM-5.3-Flash-FP4-Local-DGX-Spark-Optimized)
keeps NVIDIA's weights and supplies four vLLM patches plus a generation policy.
It configures **262,144 context**, **808,020 logical KV tokens**, four slots
and adaptive MTP. Its **+23.43% short/concurrent throughput** result is relative
to its own matched original configuration. The primary cells use 512 output
tokens, low effort and request wall time including TTFT; concurrent rates are
aggregate. Separate long-context decode-only rates have a different denominator.

That controlled patch comparison is useful evidence for that configuration;
it is not a measured improvement over this Flare release or a guarantee at 1M
context. The publisher also documents tight memory headroom and a required guard.

## How to compare a future candidate

A future experiment must first identify the same checkpoint revision and
record exported precision, sampler defaults, reasoning effort, speculation and
modalities. Keep prompt bodies, cold/warm cache treatment, output budgets,
concurrency and hardware fixed. Record per-request TTFT, end-to-end time,
decode-only and aggregate rates separately; retain delivery gaps and per-run
speculative acceptance counters. Report advertised slots alongside actual
admission and cache capacity under pressure.

Compare independent starts with a preregistered decision rule. Keep adverse
points, numerical/state checks and failed runs visible. Published peaks,
short-output averages and long-running decode rates must not share a ranking
column without their distinct methods. Pool arithmetic does not qualify
concurrent full-context retrieval.

The sources suggest future checks of larger slots, MTP depth, chunk size and
prefix reuse. Those are already research items, not recommended production
changes. Resume only from the current Flare checkpoint, with Exa research and
local engine review before critical code changes; test one treatment at a time.
