# Complete target replay on two Sparks — registered gate

> Historical architecture or qualification record. Current production, unresolved gates and the research pause: [docs/63](63-production-pause-checkpoint.md). Old window controllers must be adapted before reuse.

The pinned checkpoint has45 target layers: three dense and42 routed expert
layers. Its vocabulary is154880, hidden width4096, and the vocabulary head stores
F8_E4M3 values [154880,4096] with U8 scales [154880,128]. The metadata-only receipt
`checkpoint-target-geometry.json` retains config/index hashes. Earlier42-layer
scale-audit evidence covers the routed experts, not all target layers.

Exa reviewed the [NVIDIA model card](https://huggingface.co/nvidia/GLM-5.3-Flash-FP4-Local),
[Flare multi-host contract](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/multi-host.md),
and [numerical/replay design](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/core-design.md).
The card names vLLM as validated runtime; Flare adoption requires this separate
qualification. Pinned complete-target tests exist, but their launcher assumes
four local GPUs and PCIe collectives. Use the already reviewed local/global rank
mapping, RoCE owner and warmup handling from docs/39. The vLLM/exllamav3/TensorFold
review there supports explicit ownership, bounded preparation and same-rank
collective order; it does not establish these GPU results.

Preserve the entire upstream `_rank` method and `_inputs` helper from
`test_glm53_stack_tp_cuda.py` (SHA ab267cb0), with full-method AST identity after
documented host/preparation substitutions. Keep its45-layer and full-vocabulary
shape assertions. Select the actual A16 expert owner/calibrated A4 prefill,
native dense activations and text-only loading; assert each routed owner's
precision and retained calibration. Map global ranks0/1 to local GPU0. One RoCE
runtime supplies reduction and vocabulary gather, as serving bootstrap does;
close that shared owner once. Only compilation warmup widens collective waits.

Each rank runs capacities65 and4096. Every case executes a complete target
prefill then three single-token decode replays, checking native completion,
allocation stability, finite/nonzero hidden and rank-zero vocabulary logits,
exact hidden equality between ranks and finite recurrent state with untouched
unused slots. All original assertions remain. This is complete-target native
replay coverage, not an independent mathematical-reference comparison, exported
core equivalence, MTP generation or full state-reuse acceptance. Those gates
remain separate; do not infer them from these two cases.

Register `target-roce-window-20261116T130000Z` only after docs/46–47 same-selection layer qualification passes9/9 on each
rank and closes with independently verified B12X restoration and fallback off.
Use the existing private qualification extension, pinned checkpoint/source and
installed FlashInfer; no serving artifact, package, driver or kernel change.
Both ranks must pass2/2 with zero skips/errors/failures and actual exit0. Retain
XML, source/environment hashes, terminal states and memory samples.

Helpers in `qualification/windows/target-roce-20261116` keep the90-minute
fallback,4500-second controller,3900-second ranks and3600-second pytest limit.
Both GPU locks and idle90GiB free/100GiB available gates apply. Abort below
1.5GiB free or8GiB available on either host, including loading/compilation.
Restore B12X on completion or failure and independently verify original images,
fresh5/5 smoke, healthy API/watchdog/tailnet and absent test/native processes
before disarming fallback. A timeout remains an incomplete test, never a pass.

Window started07:38 UTC after docs/47 passed and independently closed. Source
hashes match on both hosts; the notify memory monitor is ready before model
loading. No complete-target result is claimed yet.

This initial window was aborted during first-case autotuning to preserve upstream
per-case GPU process isolation. No target test completed. All53 observed memory
samples were healthy (minimum26.56GiB free). Docs/48 records the unchanged-fixture
isolated retry. Initial-window B12X recovery/fresh5/5 closed07:49:53 UTC and its
fallback was disarmed before retry.
