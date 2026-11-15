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

Run the unchanged upstream indexer replay cases on SM121: decode2/decode32,
prefill65/prefill4096, poisoned scratch, inactive rows and exact native replay
comparisons. Run `qualification/test_glm53_state_cuda.py`: the upstream
TP4/width6 control and the deployed TP2/width4 geometry. Keep upstream bounds:
output relative L2 < .01, recurrent/history rtol .025 / atol .002, subsequent
output rtol .025 / atol .005. These are per-rank operator tests, not a multi-host
collectives test. Also run all 32 unchanged upstream GLM state-transfer cases:
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
