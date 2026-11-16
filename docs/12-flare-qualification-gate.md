# Next Flare qualification gates — registered 2026-11-15

> Historical architecture or qualification record. Current production, unresolved gates and the research pause: [docs/63](63-production-pause-checkpoint.md). Old window controllers must be adapted before reuse.

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

Subsequent Exa review of the [native CLI memory contract](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/cli-design.md)
and pinned `helios/src/runtime_core/limits.rs` establishes binary size suffixes
and fractional suffixed sizes (the parser tests1.5GiB). Thus the whole-GiB
restriction belongs to this kit's current ledger parser, not the native engine.
Before the later capacity window, evaluate a smaller reserve reduction than the
registered4→3GiB arm, using measured cache bytes and full-workload memory minima.
An eighth-GiB increment could avoid surrendering an unnecessary full GiB, but is
not yet a qualified setting or implemented launcher option. Freeze any such
parser change and register the exact reserve, predicted capacity and unchanged
memory/accuracy/performance gates before its restart. Do not apply it during the
latency-policy window or assume startup reserve equals sampled MemFree.

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


## Native dense activation export — registered before execution

Component arm 6bf1900 passed49/49 with both KDA output relative errors0.0 and
all original bounds intact. Independent variable for the next full-model arm:
`--native-dense-activations` enabled during export. Freeze checkpoint/source pins,
TP2, four slots, prefill4096, MTP3 fixed, CP-off, ordinary graphs, preparation and
serving reserve4. Do not combine reserve3 or CP with this arm. Use ordinary
export so weight payloads are checked again; retain the old core and acceptance
file. Kernel-cache keys include the activation-mode request; compiled forwards
and captured graphs are prepared anew by export.

Exa confirmed the official [CLI contract](https://github.com/NVIDIA/hyperflare-inference/blob/main/docs/cli-design.md)
and [weight reuse limitations](https://github.com/NVIDIA/hyperflare-inference/blob/main/docs/model-preparation.md).
Pinned `planning.Plan.to_dict` and multi-host export print the resolved option;
`rebuild_manifest.from_plan` omits it. The kit therefore captures each export in
a dedicated log, requires exit0, exactly one resolved plan and newly published
cache entry, and binds the primary hash to that plan in local provenance.
Acceptance must name and hash this receipt on both nodes. The serving guard
rejects a missing, changed, wrong-core or mismatched-option receipt. This is
unsigned local operational evidence, supplementing native signature and payload
verification; do not claim that the signed manifest attests to the option.
Reviewed local vLLM MXFP8, FlashInfer precision-mode cache keys, exllamav3 FP16
layouts and TensorFold W8A16/FP8 paths. No engine/kernel code is changed.

Export phase: snapshot both candidate trees/acceptance and incumbent identities,
arm automatic restoration at110minutes before stop, disarm watchdog, stop B12X
through its unit, require both memory gates. Preparation units retain their
90-minute timeout. Require both rank success, matching source/binary hashes,
resolved plan and new primary evidence. Any failure restores B12X; preserve
logs and investigate through Exa. No automatic serving/adoption at export exit.

A subsequent serving phase has a separately armed150-minute restoration deadline.
Verify the new core and fixed controls before seven API checks, cold concurrent
retrieval, full-model state tests and the full three-repetition speed matrix
against the completed B12X reference. Retain >2% robust-regression gate and
memory/quality requirements above; full capacity and lifecycle gates remain.
Do not claim speed/quality preservation from the component pass. Restore B12X
at phase completion or failure. Adoption still requires explicit approval.

## Cold concurrent and forked-prefix retrieval client

`flare_retrieval.py` retains the pinned upstream fixture/classifier (SHA256
`5a25550356fe1490e0a28bbfa755efe2bec822695b21922a6ed533d2e5aa4098`) and adds
barrier-synchronized cold requests and different suffixes after a shared warm
prefix. Run sizes8000/60000 (fixture sizes, not token lengths), c4/c8, three reps,
T1/top-p.95, four-slot cap, 1024 maximum completion tokens. Use the same run ID
on candidate and reference so request hashes match. Record actual prompt and
completion counts, cache observations, per-batch speculative counter deltas,
graph shapes and verdicts. No raw request/response text is written by this client.

Require observed cached_tokens=0 for cold requests and >0 for every fork. Stop
and retain the batch on corrupt/error responses, missing/reset/nonadvancing
metrics or a cache-observation failure. Neighbor/misplaced results are retained
as accuracy misses for the matched reference comparison, not relabeled passes.
These observations do not establish byte-equivalent hybrid state, a long-context
capacity pass, or accuracy equivalence. The ordinary/speculative comparison and
pressure/page-boundary checks remain distinct gates. Run only after the new core
has passed native startup and API smoke; the current export is unchanged.

Exa sources: the [upstream defect analysis](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/glm-batched-speculation-defect.md)
and [pinned retrieval design](https://github.com/NVIDIA/spark-local-inference/blob/main/scripts/repro_glm_batched_speculation.py).
The former distinguishes inactive planned rows from live request count and
neighboring-record misses from corrupt output. Local vLLM's hybrid-prefix test
tracks actual skipped/recomputed tokens, exllamav3 pairs target/draft snapshots,
and TensorFold shares serial/prefix KDA updates. Consequently, cache hits and
fluent responses alone are insufficient. This client measures observed reuse
without claiming it replaces the separate state checks.


## Memory evidence during native serving

Start `flare_memory_watch.py` only after native health200 and before measured
requests, in a bounded user unit. Sample head and worker `/proc/meminfo` every
five seconds, recording physical free, available and swap values in bytes.
The previously registered limits remain MemFree>=1.5GiB and MemAvailable>=8GiB
on both nodes. With `--restore-unit` naming the phase's pre-armed restoration
service, a low or missing observation queues that separate service and exits1.
It does not run restoration as a child that could be killed with the monitor.
Without that option it is observation-only, suitable for the B12X reference.
Stop the monitor before deliberate shutdown/peer-failure tests and report those
intervals separately. Samples bound observed minima, not instantaneous peaks.

Exa's [NVIDIA UMA guidance](https://docs.nvidia.com/dgx/dgx-spark/known-issues.html)
explains why VRAM-only reporting is insufficient on GB10. Local vLLM, exllamav3
and TensorFold similarly distinguish reclaimable host memory from CUDA free
memory. This client records both host measures; it changes no allocator,
checkpoint, KV layout, kernel or sysctl and does not globally drop caches.

## Loaded shutdown and peer-loss checks — registered before execution

After the performance and retrieval clients terminate, stop the enforcing memory
monitor while retaining the scheduled B12X restoration timer. Run
`flare_lifecycle.py --action graceful` in its own bounded client unit. It refuses
active benchmark/retrieval/preparation/qualification units, an active incumbent,
memory enforcement, missing restoration scheduling, or nonidle request gauges.
Keep the stream open until at least 32 generated tokens and a nonzero active
request gauge are observed, then queue a stop of the head serving unit only.
Require both ranks terminal within 180 seconds, both unit results success with
exit status zero, HTTP stream closure and both operation locks released. Capture
unit states and timing; a closed connection alone is not a clean-stop pass.

Use the scoped candidate cache-release helper and unchanged idle-memory gate
before restarting the same core through the head unit. After health and a fresh
API smoke, the independent failure-injection check uses the same active-decode
condition, then sends SIGKILL to the worker candidate unit's entire control group.
Require head failure with nonzero status, both ranks terminal within 180 seconds,
closed HTTP stream and released operation locks. This deliberately lost worker
cannot establish successful CUDA drain; it checks fail-stop propagation and
process cleanup. Capture the native logs separately. Stop this client and restore
B12X through the existing helper, then verify both original image digests,
health, five API checks, watchdog and tailnet before disarming restoration.
Do not start a lifecycle check unless enough of the serving window remains for
its restart and restoration; any timeout or unexpected result retains a failed
receipt and restores the incumbent before Exa-guided troubleshooting.

Exa's [multi-host lifecycle guidance](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/multi-host.md)
stops rank zero before peers, and the
[upstream qualification TODO](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/TODO.txt)
distinguishes socket coordination from threaded executor proofs. Pinned native
`serve_peer` retains resource owners when drain is unconfirmed; rank zero closes
the server before releasing transport. Local vLLM distinguishes requested stop
from engine death, exllamav3 drains transfer queues before releasing states,
FlashInfer synchronizes collective resources before close, and TensorFold closes
its HTTP server in a SIGTERM cleanup path. These support the checks; they do not
prove this two-host run correct. No engine or launch configuration changes are
combined with these tests.

## Comparing completed matrices

`flare_compare.py` accepts only complete matched three- or five-repetition
matrices. It rejects missing/duplicate rows, different manifests/request hashes,
unequal prompt counts, noncold or inexact prefills, decode lengths other than200,
invalid timing, and speculative rates inconsistent with their measured deltas.
It retains every repetition and reports per-request and aggregate rates
separately. Within each repetition, per-request rates use the batch median;
across repetitions the comparison uses the median again. Concurrency8 still
has four execution slots, so its TTFT includes queuing.

For descriptive separation, label a regression robust when even the best
candidate repetition is below98% of the worst reference repetition. A median
regression greater than2% whose ranges overlap remains inconclusive and requires
more repetitions; it is not called a pass. This supplements the existing2%
gate, without claiming a confidence interval from three observations. A speed
report cannot override separate quality, capacity, memory or lifecycle failures.

Exa's [official benchmark definitions](https://docs.vllm.ai/en/stable/benchmarking/cli/)
distinguish aggregate throughput from per-request latency and explain that
speculative streaming emits token bursts. The already frozen client includes
the first burst in its decode numerator; both engines use that same definition,
which is explicitly not inverse standard TPOT. The
[acceptance metric definitions](https://docs.vllm.ai/en/latest/features/speculative_decoding/acceptance_metrics/)
support the accepted/drafts formulas. Local vLLM benchmark source was checked
against these definitions. No running measurement client or engine is changed.

## Full-layer scale-population audit — separate idle window

`flare_scale_audit.py` addresses the source-identified packed A16 scale boundary
in `10-flare-precision-audit.md`. It uses the pinned independent CPU CSF decoder,
then partitions logical scales for both TP2 ranks and accumulates all288 experts
before calculating each projection's scale-lifting factor. Gate/up share the
W13 population; down has its own W2 population. The report binds shard headers
and all scanned scale payloads by hash, and contains counts rather than weights.

First scan target layers3,24,44, each with every expert, within a30-minute unit
limit. This is a selected-layer investigation: zero affected counts do not clear
the other target layers or the remaining MTP/packing/replay gates. A nonzero
count establishes that source scales meet the pinned packed encoder's discard
condition; it does not by itself measure native output error or prove that an
alternative representation is selected. A later `--layers all` scan covers all
target CSF layers3..44 and must have its own bounded window.

Run only after the serving matrix/retrieval/lifecycle window closes and B12X
restoration is verified. Snapshot the unchanged candidate/core and incumbent,
pre-arm a45-minute B12X restoration timer, disarm the watchdog, stop B12X through
its unit, and pass both original idle-memory gates. The new timer's restoration
command must stop the exact transient scale-audit unit before invoking
`flare_restore.sh`; that helper does not discover arbitrary client units. Use
`RuntimeMaxSec=1800`, `TimeoutStopSec=30`, `KillMode=control-group` for this audit.
The script holds the candidate operation lock and refuses active head GPU or
incumbent units. Set `CUDA_VISIBLE_DEVICES` empty and run in the already pinned
Flare preparation uv environment; no dependency installation or CUDA work.
Retain partial output on timeout/failure, stop the audit unit, then restore and
verify the incumbent before disarming the timer. No source/checkpoint, serving
reserve, runtime quantization, or host driver/kernel changes are combined here.

Exa's related [Marlin scale report](https://github.com/sgl-project/sglang/issues/48906)
and [rescaling change](https://github.com/vllm-project/vllm/pull/34577) were checked
against pinned FlashInfer's actual `_csf_preparation.py` and packed-scale helper.
The local vLLM fallback shares this boundary; it is not the incumbent B12X path.
Flare's independent CPU decoder supplies checkpoint bytes, while TensorFold and
exllamav3 reinforce the distinction between stored quantization and execution
arithmetic. No numerical tolerance is introduced or relaxed by this audit.

## All-target-layer scale audit — registered after the selected-layer result

The selected layers 3, 24 and 44 completed in 236 seconds, with all 288 experts
and both TP2 partitions, no scales below the boundary and a 2.51 GiB recorded
memory peak. These results do not clear the remaining 39 target layers.

Next scope: the same frozen `flare_scale_audit.py --layers all`, target layers
3 through 44, every expert and both ranks' logical scale partitions. Freeze
checkpoint, independent decoder revision, audit script hash, binary, accepted
core, recipe and all runtime settings. No dependency or representation change.
Require 168 unique population rows plus manifest and completion (170 lines),
the expected full populations, payload/header hashes, and CUDA uninitialized.
Any nonzero affected count requires native packing/output investigation before
precision preservation can be claimed. Zero counts still do not prove native
packing, A4-prefill arithmetic, MTP or full-model equivalence.

Use a new separately snapshotted window only after the preceding B12X
restoration is verified. Pre-arm a 90-minute restoration timer whose command
stops the exact audit unit before invoking the existing restore helper. Disarm
the watchdog, stop the incumbent through its unit and require both original
idle-memory gates. Run with empty CUDA_VISIBLE_DEVICES, the existing pinned uv
environment, RuntimeMaxSec=4200, TimeoutStopSec=30 and KillMode=control-group.
The 70-minute execution bound includes margin above the roughly 55-minute
linear estimate; an estimate is not permission to extend a live job.

Retain this transient unit with `--remain-after-exit --service-type=exec`.
Capture LoadState=loaded, SubState=exited, MainPID=0, Result=success and the
actual main-process code/status before explicitly stopping it. Require the
complete validated output as well. Do not read defaults from a collected unit
as an independently retained exit code. On timeout/failure retain partial data,
stop the client, restore B12X, verify images/health/smoke/watchdog/tailnet, then
disarm the timer. The [official systemd-run reference](https://freedesktop.org/software/systemd/man/latest/systemd-run.html)
supports retained completion state; Exa and the unchanged pinned scale-decoder
review above support this larger audit scope. No new GPU treatment is combined.

## Later capacity observations — 2026-11-16

The original 2,295,552-token observation is not a constant of the accepted core.
Two later starts at the same 4 GiB reserve logged 2,323,456 and 2,335,232 tokens.
Both remain below the unchanged 2,350,210-token adoption requirement. Capture
live `flare_total_kv_pages`, `flare_kv_page_tokens` and `flare_total_kv_tokens`
at every fresh comparison start, checking pages times page size equals capacity.
These metrics describe the per-rank pool before checkpoint retention.

Exa revisited [NVIDIA's GB10 memory discussion](https://github.com/NVIDIA/flare-local-inference/issues/73),
then pinned runtime memory sizing, Selene MemAvailable accounting and the core
loader. Sizing depends on observed available memory and measured allocations.
The loader already releases core-file page cache before context/cache allocation;
an additional live cache flusher is not proposed. The initial 2.33% shortfall
remains historical evidence, not a precise prediction for a future reserve arm.
Use the fresh capacity and full-workload physical-memory minima to register any
fractional-reserve experiment. No reserve or kernel watermark changed here.
