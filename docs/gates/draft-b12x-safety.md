# TODO3: qualify the actual draft-B12X arm safely

Pre-registered fresh window for TODO3 itself. The first paired attempt never
started B because Humming A failed startup. Subsequent common postload0.80
bound protects target/MTP weight processing, but retained Humming startup
still fails the2GiB host floor (startup-bound-retry). Failed cache/heap/lookup
trials are not adopted. Do not repeat unsafe A for a speed number.

This tests B against the retained failed A with identical common trace/bound,
image/checkpoint/quant/17G controls. It can establish B startup support, safety,
functional behavior and healthy-only speed. It cannot establish a fresh paired
throughput gain or complete TODO3's performance comparison without a safe A.
Keep TODO3 open and report this limit; no automatic adoption.

One treatment: only speculative-config.moe_backend humming→b12x, exactly as
the original candidate. No native cache/IR cleanup or other launcher knobs.
Driver labels the sole recipe arm a in filenames; semantically it is B, not a
new Humming control. Experiment metadata records draft-b12x-only.

Fresh Exa re-evaluation of the [same NVIDIA card](https://huggingface.co/nvidia/GLM-5.3-Flash-FP4-Local)
finds a newer B12X draft launch, which changes many other controls and is not
copied. The [target-only NVFP4 integration](https://github.com/vllm-project/vllm/pull/39634)
excludes BF16 drafts, not this independently header-verified NVFP4 MTP. Earlier
receipt ab-draft-b12x/mtp-format.json proves864U8 expert matrices,864F8 scales
and864F32 globals at pinned76348ddb using headers only. No requantization.
Local vLLM speculative overrides, actual installed NVFP4 adapters, FlashInfer
packed MoE contracts, EXL3 lifetimes, TensorFold bounded ownership and Flare
MTP preparation reviewed. DFlash, adaptive draft depth, different quantization,
capture policies and newer images are separate treatments and stay frozen.

Controls: image3b5da79c on both nodes, checkpoint76348ddb, TP2/RoCEnante,
targetb12x/B12X, draftattentionB12X,MTP3,4seats,1Mcontext,4096batch,17G FP8 KV,
block256/pool2,350,210, default allocator, prefix/chunking and Max reasoning.
Common passive trace and0.80 target/MTP postload bound restored1.0; identical
driver/kernel, observer/log lifetime, measurement prompts/seed/budgets/code.
No prior cleanup or terminal ownership mod. Fresh process/prefix state; keep
pinned content-addressed disk JIT cache and warm once before measurement.

Before restart: final independent Astra review of this concrete recipe/config,
all CPU/lifecycle and pinned frontend checks, one-string comparison versus
common-bound Humming recipe, both immutable images/source/runtime hashes,
env snapshots, freshoutput and usual>=90GiB free/>=100GiB available gates.
Existing image kernels are selected; no new CUDA or packing implementation.

Before measurement: actual both-rank profile must request b12x and boot logs
must prove resolved B12X NVFP4 MoE, with no Humming fallback. Full target/MTP
trace+bound scopes/hashes/PID/order/minima>=4GiB, all observedhostsamples>=2GiB,
health200, exact KV pool, smoke5/5 including Max reasoning and parity. If health
fails or backend is unsupported, stop; no benchmark or improvement claim.
If healthy run once-warmed20cold-prefill cells8k..128k/c1,2,4,8 and3x200-token
post-ladder decode reps/concurrency with per-run acceptance deltas. Repeat
noisy/flagged cells before interpretation. Historical A matrix is context,
not a contemporaneous paired comparator for this changed common startup setup.

Unit b12x-recipe-window@draft-b12x-safety, single-use local/ab-draft-b12x-safety.
All outcomes including success remain stop-only: canonical ledger restored,
both model objects absent, proxy/watchdog off. No unsafe recovery boot, floor
relaxation, smaller17G pool, automatic adoption or TODO3 completion claim.

Measurement plumbing correction: pool formatting now invokes `uv run --offline python -c`, rather than unsupported `uv run -c`. [Official uv command documentation](https://docs.astral.sh/uv/guides/projects/#running-commands) and [script alternatives](https://docs.astral.sh/uv/guides/scripts/) were checked through Exa, followed by local launcher/tree usage. Validate the exact invocation with installed head uv before any model start; lifecycle fixture also recognizes only the corrected invocation. This has no serving-configuration effect.
