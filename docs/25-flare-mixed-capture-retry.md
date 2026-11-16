# Mixed native capture: retain failure and reduce reader contention

> Historical architecture or qualification record. Current production, unresolved gates and the research pause: [docs/63](63-production-pause-checkpoint.md). Old window controllers must be adapted before reuse.

The docs/24 balanced client completed25 requests/3 cases with37 passing memory
samples and both invocation-bound native exits0/no forced kill. Its capture has
399 consecutive completion fences1..399, but the old shared loss counter is1.
That counter covers completion, latest-dispatch and sampled-state writes. The
record does not identify which update was lost. The original zero-loss gate
therefore fails; no latency arm ran and the guarded helper restored B12X.
Retain `mixed-diagnostic1-*` receipts without reclassifying the failed capture.

## Exa evidence and local reconciliation

[Perfetto buffer documentation](https://perfetto.dev/docs/concepts/buffers)
distinguishes producer staging loss, central-buffer overwrite/discard and flush
latency. Buffer sizing must cover peak bursts and consumer scheduling delays.
The [Linux tracing design](https://docs.kernel.org/trace/ring-buffer-design.html)
explains that overwrite and producer/consumer modes both lose records when full.
Neither source makes a missing record safe for complete sequence analysis.

Pinned Flare uses a1024-entry deque guarded by a mutex. Producer writes use
try_lock; reader contention increments the same counter as buffer overflow.
Only399 completions were produced in this trial, so the observed loss cannot be
capacity overflow. The500ms consumer polls share a lock with submitted,
completed and sampled-state writes. The first correction reduces diagnostic
polling to5s and adds a separate completion-loss counter. It preserves bounded
memory/output, nonblocking producers, exclusive output creation and the original
strict `complete = !truncated && dropped_updates == 0` verdict. A lost sampled
state still fails the gate. The added fields identify the loss; they do not
excuse it. Sampled state is now coarser and must not establish an absent event.

A stronger alternative is a dedicated preallocated lock-free completion queue.
[Crossbeam ArrayQueue source](https://github.com/crossbeam-rs/crossbeam/blob/main/crossbeam-queue/src/array_queue.rs)
provides bounded enqueue semantics. A [tracing performance issue](https://github.com/tokio-rs/tracing/issues/3446)
illustrates queue/consumer wakeup contention, but its measurements are not this
hardware. Neither ArrayQueue nor rtrb is in the current locks; changing queue
ownership/dependencies is larger than needed for this low-rate diagnostic and
remains an alternative if the bounded polling correction still loses updates.

After Exa, revisited local Flare metrics/capture ownership, vLLM metric hooks,
exllamav3 generator and TensorFold scheduler. Their application-level progress
reporting does not supply a drop-free native Flare completion queue. No change to
kernel, weights, KV, active scheduling policy or graph prices is combined here.

## Registered retry and build

Use `mixed-trace-window-20261116T033000Z`. Freeze the corrected observer in Git;
apply it after the unchanged latency patch to Flare5a4e8679 in a fresh worker
worktree. Verify both Cargo locks unchanged. Run native scheduler, dashboard,
metrics, config and CLI tests, then release build; retain actual terminal status
and manifest/binary hashes. Local Python suite66 tests passes, including strict
rejection of one-repetition performance comparisons. Rust/hardware are pending.

Arm a90-minute fallback before stopping B12X. Its helper stops the head
orchestrator, both memory watches and the exact worker build unit before the
original restoration helper. Snapshot both ledgers, runtime hashes and images.
Use the same90GiB-free/100GiB-available gate before building or starting. Build
with two jobs, no CUDA execution, only while both models are stopped.

After build, run both balanced and latency on that same new artifact/core with
head-only tracing and unchanged docs/24 controls. Fresh restart each arm. Verify
actual executable/argv, manifest and core before the matched one-rep client.
Enforce1.5GiB-free/8GiB-available; retain25 matched requests/3 cases, exact cold
usage and hashes, both actual native exits0/no forced kill, complete contiguous
histories, zero dropped updates and no truncation. No traced timing is a speed
gate. Any test/build/trace/memory failure triggers B12X restoration.

Restore B12X after both captures. Verify original images, health200, fresh5/5
smoke and watchdog/tailnet, append rollback selection, then disarm fallback.
Production adoption and merge remain gated by docs/23. No boot or host upgrade.

## Initial build result

The native test build stopped with exit101 before any candidate start. A test
helper still called `metrics.write` without the new completion-kind boolean;
Rust reported E0282 at that closure. The producer call sites were updated, but
this test call was missed. Corrected it to `metrics.write(false, ...)`, matching
its dispatch update. [Rust's call contract](https://doc.rust-lang.org/error_codes/E0061.html)
was checked through Exa; all four call sites were then re-read. No runtime policy
or numerical change is part of this correction. Keep the failed build receipt
and rerun the native suite. Automatic B12X restoration started at03:29 UTC.

The corrected-call retry uses fresh window/worktree suffix20261116T034000Z and
the same registered controls, tests,90-minute guard and automatic restore on
failure. The failed build/worktree remains intact. Freeze the corrected patch
(commit50373ad) before staging; no scheduler formula changes are included.

The compile-failure rollback was verified03:35:13 UTC: both original images,
health200, fresh5/5 smoke, active watchdog/tailnet and no native rank processes.
Fallback disarmed03:35:14 UTC. The fresh corrected-call build started only after
this closure and both-node idle memory gates passed (head115/114GiB, worker
116/115GiB free/available).

## Native build passed; serving transition rejected before startup

Native dashboard/capture13, metrics4, scheduler-filter316 (2 manual benchmarks
ignored), config2 and CLI1 tests passed. Release build completed with both locks
unchanged and retained actual exit0. Manifest
`de4c3f7cc9cefe0e8cf59c3844865be01caf2006e109bcbe8d4f45b9561f769d`, binary
`7c27ae5e90e6b7cf7008717397313b52e8668375ec8c05f7c235b6d63d1001cb`, observer
patch8ce9b2d7, kit commit50373ad. The latency policy patch is unchanged338bbeb0.

The orchestrator then used `uv run --python /usr/bin/python3 -c` without the
`python` command. uv rejected it before candidate startup and restoration began.
[uv interpreter selection](https://docs.astral.sh/uv/concepts/python-versions/)
was checked through Exa. Correct syntax is `uv run --python /usr/bin/python3
python -c ...`; no native rebuild is needed. Both artifact files were staged
atomically and their hashes verified independently on the head before another
production stop. `flare --version` passed. The failed command log is retained.

The serving-only retry is `mixed-trace-window-20261116T035000Z`, with the exact
manifest/binary above pinned directly. Pre-arm60-minute restoration; no build
step or dynamic artifact discovery occurs after production stop. Keep all prior
controls, both cold arms, zero-loss/contiguity gates, memory enforcement and
verified B12X restoration. Verify helpers/CLI syntax and both artifact hashes
before entering the window. This is a diagnostic, never an adoption verdict.

Serving-only preflight passed on both nodes using the actual launcher provenance
checks while B12X was healthy. B12X closure was verified03:47:28 UTC with both
original images, health200, fresh5/5 smoke and watchdog/tailnet active; the prior
fallback was disarmed03:47:29 UTC. The new60-minute guarded window passed both
idle-memory gates and started balanced on artifactde4c3f7c. Native trace and
mixed-client validation are in progress; no production decision yet.

Both captures completed with zero lost updates, complete contiguous histories,
matching request bodies and work. Balanced414/native records, latency402;37/36
memory samples passed. Both native exits0/no forced kill in each arm. Native
graph timing evidence and its limits are recorded in docs/26. Automatic B12X
restoration completed; final fresh smoke/closure is being retained.
