# Native completion observation and scheduler qualification

The native headless service does not enable Flare's terminal telemetry. The
candidate adds `--scheduler-trace PATH`, using the existing nonblocking completion
buffer and a separate writer. It preserves slot/generation identities, submitted
positions and token counts, graph identity, selection/commit/completion times,
and observed GPU durations. These are completion observations, not GPU start/end
timestamps or kernel attribution. No prompt text, token IDs or output text is stored.

The capture is limited to 600 seconds, 16 MiB and 16,384 completions. Existing
files are rejected. Buffer drops, output truncation or a missing success footer
make it incomplete evidence. The collector shares dashboard ownership and its
stop/join path; it does not change GPU drain, admission or scheduling. Startup
capture errors use the normal coordinated shutdown before returning failure.
Performance measurements run with capture explicitly off.

Exa rationale: [native telemetry](https://github.com/NVIDIA/flare-local-inference/blob/main/helios/README.md)
already separates observation from execution; [performance guidance](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/performance-work.md)
requires separating replay, scheduling and HTTP time. Rust's
[file creation contract](https://doc.rust-lang.org/std/fs/struct.OpenOptions.html)
supports exclusive output creation. A bounded channel was considered; the existing
preallocated buffer avoids adding another producer queue. Nsight remains the
stronger option for kernel attribution, which this host-order diagnostic does not claim.
Pinned vLLM profiling, exllamav3 prompt rotation, TensorFold remaining-work selection,
and FlashInfer tracing were reviewed before the change; none supplies this native
per-request completion stream without integrating with Flare's execution owner.

## Registered window

The window may begin only after the all-layer audit restoration is verified.
Snapshot both runtime ledgers, core/launcher/CLI hashes, unit enabled states and
incumbent image identities. Arm an automatic B12X restoration service for 180
minutes, stopping the exact CPU build and measurement units before restoring.
Stop the incumbent watchdog and B12X through systemd; require MemFree at least
90 GiB and MemAvailable at least 100 GiB on both nodes. No serving or builds overlap.

Build on the worker using `qualification/build_scheduler_trace.sh` in a fresh
isolated worktree. Apply the unchanged latency patch and the separately frozen
trace patch, keep both Cargo locks unchanged and use offline dependencies. Run
dashboard/capture, scheduler-metrics, scheduler, config and CLI tests before the
release build. Retain actual exit status and test counts; manual ignored planning
benchmarks are not passes. Stage the immutable manifest/binary on both nodes,
verify their hashes, and record the resulting identity before any Flare restart.
The first candidate trace patch is
`fe710520b3b0d6e04d7a0e97b074cd582bc793803a82eca34f96feb3afdf5c85`.

The existing core, checkpoint, TP2, four slots, MTP3, chunk4096, CP-off, reserve4
and sampling remain fixed. Use the same built binary for balanced and latency.
Append native-arm/policy/capture settings; never edit earlier ledger assignments.
The trace filename resolves under the candidate runtime's `local/`; rank1 does
not receive the capture argument. Verify actual argv and both binary hashes.

For each policy, start through the head unit and observe the existing two-node
memory bounds (MemFree >=1.5 GiB, MemAvailable >=8 GiB). Run one exact cold
four-request131072-token prefill cohort with the existing benchmark client,
same seed20261115 and one output token per prompt. Its two200-token decode rows
are diagnostic only. Stop clients and both ranks, retain trace/footer and native
terminal state. Require all four complete prompt histories, coherent monotonic
fences and request generations, exact prompt work, no lost records and matching
client hashes. Determine actual service order from those records; do not infer it
from CPU tests. An unexpected order requires diagnosis before the speed matrix.

After this diagnostic, append `FLARE_SCHEDULER_TRACE=off` and restart with the
unchanged core/binary/policy. Run the untraced API smoke and mixed workload for
each policy, then the full latency matrix and loaded lifecycle gate from docs/18.
The diagnostic runs do not replace any of those repetitions. Register the built
artifact and any client updates before serving; docs/18's earlier binary identity
is superseded only by that explicit record.

On failure, memory violation or deadline, stop clients and both native ranks,
then restore B12X. Verify original images, health, fresh five-check smoke and
watchdog/tailnet before disarming fallback. Ledger rollback is native arm upstream,
balanced policy and trace off. Numerical, long-context and capacity gates remain
required before authorized production adoption and reboot qualification.
