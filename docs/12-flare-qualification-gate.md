# Next Flare qualification gates — registered 2026-11-15

Production remains B12X while its full reference client benchmark runs. The
first Flare trial is recorded in `11-flare-trial-20261115.md`; its short timings
are not an adoption comparison. These gates precede new GPU qualification or
serving-reserve changes.

## Matched reference and full performance matrix

Replay the exact original Flare retrieval request bodies on B12X with the same
seeds, temperature 1, top-p .95 and omitted reasoning effort=Max. Warm the cached
batches once. Publish request/response hashes, usage and verdicts without raw
synthetic prompts/answers. A neighboring-record miss alone cannot identify an
engine defect; retain all misses and compare independent numerical evidence.

Run `flare_bench.py` with seed 20261115, three reps, exact lengths
8192/16384/32768/65536/131072 in that order, c1/2/4/8, four-slot cap, and
200-token prose/code decode. Warm once. Require exact prompt counts and zero
observed cached tokens for every prefill. Capture per-request TTFT, actual
completion length, decode rate, aggregate throughput and per-run speculative
deltas. Retain intermediate results if any request or observation fails; do not
restart a live job merely because a polling call times out. Reference client
unit `b12x-flare-reference-bench.service` is bounded to 150 minutes and does not
change the production recipe. External generation traffic invalidates counter
attribution and must be reported if observed.

The current exported Flare core at 4 GiB reserve is the engine-comparison arm.
Freeze checkpoint, core, native binary, TP2, four slots, prefill4096, fixed MTP-3,
no context parallelism, prompts and sampling. A robust >2% regression against
matched B12X measurements fails preservation. Report noise and all repetitions;
do not accept from a single short generation. Numerical failure prevents
adoption regardless of speed.

## Component numerical qualification window

After the reference client is terminal, snapshot both runtime manifests and
arm timed B12X restoration before stopping production and its watchdog. Confirm
both incumbent containers are gone and both nodes satisfy 90 GiB MemFree and
100 GiB MemAvailable. Maximum window: 90 minutes, with restoration at deadline.
No host package, driver, kernel, source pin, quantization or serving binary change.

Build only the pinned Heliopause extension's `qualification,extension-module`
features with locked Cargo dependencies in the candidate tree, then expose that
extension through a qualification-only Python import path. Keep the ordinary
preparation environment and accepted core unchanged. The serving CLI must retain
its recorded hash. Do not count skipped CUDA tests as passing.

First run 12 checkpoint tests derived from the pin: four NVIDIA mixed-projection
cases, six CSF expert partition/scratch cases (TP2 and TP4), and two MTP expert
packed-weight/scale cases. Require byte equality, with no tolerance substituted.
The six target-expert cases use the loader's default A4 owner; they establish
that path's packed weights and CSF reconstruction, not the deployed A16 owner's
packing or activation arithmetic. Keep that distinction in the receipt. The
older generic dense/attention tests target another checkpoint and are excluded.
The MTP test's capture wrapper forwards `allocate`/`scale_scratch` keyword
arguments used by the pinned loader; all original byte-equality assertions are
retained in `qualification/test_glm53_mtp_weights_cuda.py`.
Each set has a bounded timeout; the overall 90-minute restoration deadline
still applies, and interrupted or skipped cases remain unqualified.

Run the upstream indexer replay cases on SM121: decode2/decode32,
prefill65/prefill4096, poisoned scratch, inactive rows and exact native replay
comparisons. `qualification/test_glm53_indexer_cuda.py` uses production MLA's
`prepare_projection` factory: the old quantized-only fixture failed to bind
this NVIDIA checkpoint's `GroupedLinearWeights` before reaching any replay
measurement. The four original equality/allocation checks and test cases remain
unchanged; the first failed receipt is retained. This fixture adaptation does
not change the serving engine or establish numerical success until rerun.
Run `qualification/test_glm53_state_cuda.py`: the upstream
TP4/width6 control and the deployed TP2/width4 geometry. Keep upstream bounds:
output relative L2 < .01, recurrent/history rtol .025 / atol .002, subsequent
output rtol .025 / atol .005. These are per-rank operator tests, not a multi-host
collectives test. Also run all 31 unchanged upstream GLM state-transfer cases:
TP2 immutable snapshots/forked restores, partial pages around 256/512-token
boundaries, rejected commands preserving bytes, and MTP trailing-page aliases.
These check raw state transfer; full-model pressure/reuse qualification remains
separate. The next native smoke must cancel during at least 32 generated tokens
of active decode and observe one cancellation with zero active, inflight and
retiring slots within ten seconds before successful subsequent generation.
Fail on nonfinite values, bound violations, skipped cases or
missing native qualification support. Preserve failures and investigate through
Exa before changing code or kernels. No threshold relaxation.

Stop qualification units, restore B12X via the tested helper, verify both image
identities, health, five-check smoke and watchdog before disarming the timer.

## Later reserve-only trial

Only after the preceding numerical gate permits proceeding, test the same
accepted core with serving reserve **4 → 3 GiB**. The independent variable is
`FLARE_SERVE_RESERVE_GIB`; preparation reserve remains 4 GiB. The launcher reads
only this decimal integer from the append-only `.env` ledger, without evaluating
shell text. Append the same block on both nodes after a snapshot:

```sh
# --- serving-reserve3 <UTC timestamp> ---
# Independent variable: serving reserve 4 -> 3 GiB
# Frozen: accepted core/binary/checkpoint, TP2, CP-off, four slots, MTP-3, prefill4096
# Gate: capacity >=2350210 tokens, numerical/API/state checks, full matched speed
# Memory: MemAvailable >=8 GiB and MemFree >=1.5 GiB on both ranks during stress
# Rollback: append FLARE_SERVE_RESERVE_GIB=4; restore B12X through its unit
FLARE_SERVE_RESERVE_GIB=3
```

Require argv `--memory-limit -3G` on both ranks, unchanged core/binary hashes and
measured native cache allocation. Verify long-context admission/retrieval and
repeat the complete speed matrix against 4 GiB; no robust >2% regression. Monitor
physical memory while serving; stop on either memory threshold, allocation stall,
transport error, corruption or failed numerical/API checks. A planner token count
alone is insufficient. This is an experiment, not an adopted setting.

A separate 4 GiB serving-reserve block is the revert. Restore the incumbent after
the trial unless production adoption is explicitly approved. Keep the tested core
and runtime snapshots; never overwrite an executing launcher.

## Research basis and stronger option

Exa located the [runtime memory controls](https://github.com/NVIDIA/hyperflare-inference/blob/main/docs/model-preparation.md):
serving reserve replaces the exported reserve and does not require re-export.
Pinned `helios/src/runtime_core/memory.rs` retains an additional 2 GiB host
allowance, 5% integrated-system allowance and driver margin. A smaller reserve
still trades away physical headroom; it is not a free optimization.

Context-parallel cache sharding is the stronger capacity option without reducing
reserve. [Issue 276](https://github.com/NVIDIA/hyperflare-inference/issues/276)
is still open: shared prefill artifacts embed rank-local gather guards. Preserve
guard checks and qualify rank-specific variants before attempting that export.
Local vLLM's GLM DCP selector, exllamav3's latent-cache accounting and TensorFold's
KDA replay/cache ownership were reviewed; none supplies a drop-in fix for Flare's
compiled gather contract. The operator gates address the pinned upstream
[numerical TODO](https://github.com/NVIDIA/hyperflare-inference/blob/main/docs/TODO.txt),
not an assumption that all upstream configurations are broken.

The cancellation and raw state-transfer checks follow pinned upstream
[protocol tests](https://github.com/NVIDIA/hyperflare-inference/blob/main/tests/server/test_protocols.py)
and [GLM state-transfer tests](https://github.com/NVIDIA/hyperflare-inference/blob/main/tests/recipes/test_glm53_state_transfer_cuda.py).
Exa's model-preparation documentation distinguishes full hybrid continuation
state from KV-only reuse. Local vLLM disconnect handling, exllamav3 page/state
release and TensorFold cancellation/state ownership were reviewed before the
stronger test was implemented. Live qualification is still required.

## Sampling compatibility clarification

Exa returned conflicting upstream API text: an older logprob paragraph says
temperature zero is rejected, while the sampling section says it is clamped.
Pinned `helios/src/server/request.rs::sampling_parameters` and its boundary tests
resolve this: numeric values are clamped before validation. The GLM recipe
permits temperature .95–1 and top-p .95–1, so temperature zero becomes .95; it
does not request greedy decoding. `/v1/models` exposes these ranges. The first
trial did not establish a native HTTP rejection, and earlier kit wording has
been corrected. Both benchmark arms remain explicitly at temperature 1/top-p .95.

In the next native smoke, verify that numeric zero is accepted and a string
temperature is rejected, while recording the signed advertised ranges. Client
workflows requiring actual greedy decoding remain incompatible; do not silently
describe clamping as parity. A change to sampler semantics would require its own
source review, numerical gate and deployment window, not a reserve-only trial.

Other numeric parameters without a declared interval remain fixed at their
prepared defaults, including neutral penalties in this core. Clients must not
assume that a successful request means their requested distribution was honored.

## First numerical window and diagnostic follow-up

The 2026-11-15 first numerical window failed: TP2/width4 KDA relative L2
0.03793176 and TP4/width6 0.02955953 both exceeded .01. The four old indexer
fixtures failed during mixed-projection binding, before numerical replay.
All 12 weight checks and all 31 collected state-transfer cases passed without
skips. The registered count of 32 state cases was a counting error: pinned
parameters contain 9 + 10 + 10 + 2 = 31 cases (19 TP2, 12 TP4). Source collection
and XML agree; no test is dropped. The corrected total is 49 cases.

Before a follow-up window, freeze the indexer fixture adaptation and KDA stage
observations in the kit. Keep source pins, serving CLI, checkpoint, accepted core,
reserve and all numerical bounds unchanged. Use the same idle-memory gate and a
new 90-minute restoration timer. The indexer uses the production projection
factory, retaining every original replay assertion. The original KDA graph
comparison executes first. Only on failure, diagnostic eager calls clone input
projection, convolution, gates, gated recurrence and output values, then report
finite/error summaries without tensors. Those observations can alter timing and
cannot replace the original result, establish a serving fix, or justify adoption.
Restore B12X after the window; a reserve-only trial is not permitted by the
current failed numerical result.

Exa confirmed the NVIDIA mixed-projection contract in upstream preparation docs
and the exact [state-transfer parameter lists](https://github.com/NVIDIA/hyperflare-inference/blob/main/tests/recipes/test_glm53_state_transfer_cuda.py).
Pinned production `glm53/mla.py` uses `prepare_projection` for `qkv_a_proj`.
The KDA investigation also reviewed vLLM's FP32 recurrence, exllamav3's recurrent
rollback and TensorFold's shared serial/prefix state-update routine. PyTorch's
[numerical accuracy guidance](https://docs.pytorch.org/docs/2.15/notes/numerical_accuracy.html)
explains why batched and sliced calculations can differ; it does not authorize
relaxing this gate. Stage measurements must establish the cause before a fix.

## Native dense activation component arm — registered before execution

The diagnostic rerun reproduced both KDA errors. Its first substantial stage
error was input projection (relative L2 .02567028 TP2 / .02558133 TP4), before
convolution/recurrence; TP2 beta, forget gate and output gate matched exactly.
All four corrected indexer cases passed native replay. This evidence supports
investigating projection arithmetic; it does not yet identify the selected
kernel modes or prove a fix.

Next independent variable: `RecordedPreparationSession.native_dense_activations`
false → true, the session option wired from the official
`--native-dense-activations` flag. It changes dense `auto` to `quantized` (A8 for
FP8, A4 for FP4) while retaining explicit recipe and routed-MoE precision. Keep
checkpoint/weight bytes, TP geometries, chain seed, recurrence kernels, all
bounds and the current exported serving core unchanged. This is a component
experiment; do not re-export or adopt from the option's availability alone.

Run `test_glm53_native_activations_cuda.py`, which calls the original complete
KDA test with that one option true. Record the effective option and resolved
input/output projection selections. Require both TP2/width4 and TP4/width6 to
pass the original output L2, every accepted-prefix state/history bound and
subsequent decode checks. Retain the auto-control test and both failed receipts.
The other 47 qualification cases remain the same. No skips or relaxed bounds.

Freeze and stage this arm before a new idle-cluster window, with snapshots,
90-minute automatic B12X restoration and the unchanged memory gate. Restore
B12X after collection. If component results pass, a separate candidate export
must prove the option in its preparation metadata, native lifecycle, full-model
correctness, unchanged quantization/capacity and complete speed matrix before
adoption is considered. No serving reserve change is combined with this arm.

Research: Exa returned the [official flag contract](https://github.com/NVIDIA/hyperflare-inference/blob/main/docs/cli-design.md).
Pinned `glm53/recipe.py` forwards the option and `components/linear.py` selects
quantized activation mode when enabled. Local vLLM's MXFP8 backend calls native
b12x MXFP8 linear; TensorFold distinguishes W8A16 and FP8 activation arithmetic;
exllamav3 uses its own weight layouts. Fixed A16 arithmetic is another possible
accuracy-oriented arm, but neither it nor native activations is assumed to
preserve speed without measurement. No alternative engine or checkpoint is used.
