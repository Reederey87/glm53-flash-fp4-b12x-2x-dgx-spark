# Temporary PCP bound passed the model-free physical gate

Reviewed commit e2ee283 ran one fresh A0 then B512 process/node. The corrected
transaction exited0; both policy resets/readbacks, no-container checks and timer
cancellations passed. Preflight084548Z is retained separately: worker-ledger
layout abort before any GPU probe, timer, lease or policy write.

| Measurement | Head A0 | Head B512 | Worker A0 | Worker B512 |
|---|---:|---:|---:|---:|
| Immediate available gain MiB | -0.219 | 524.297 | 0 | 523.688 |
| Original physical gate | Fail | Pass | Fail | Pass |
| Allocation-plus-fill ms | 240.172 | 241.923 | 233.906 | 232.562 |
| Pre-fixture PCP stock MiB | 973.145 | 201.438 | 956.613 | 202.949 |
| Release PCP delta MiB | 522.820 | -9.586 | 522.176 | -11.141 |
| Release buddy delta MiB | 0 | 532.582 | 0 | 533.500 |

All four retire512MiB idle allocator ownership while preserving the active1MiB
owner, device counters, effective default host backend and original pointers.
Three prepared-B12X and three pinned-copy graph replays/process pass with
compiler/loader forbidden. Both B nodes independently pass the original source/
PID/state/idle/128MiB physical validator. A's valid physical-only failures remain
failed; incomplete controls cannot authorize B.

Readback proves512 and source-derived high_min=high_max bounds with unchanged
base batches on both20-CPU/4KiB nodes. PCP stock reduction already exists before
the fixture; around release, B's buddy gain and available gain demonstrate a
separate return interval. System-wide non-atomic counters do not identify the
individual fixture pages. One timing sample/arm does not qualify throughput.

Restored0 at08:50:34Z head/08:50:35Z worker, min_free1048576/stat_interval1
unchanged. Head-only launch ledger has snapshots/comments; no worker ledger was
created. No persistent sysctl configuration, driver or kernel change. Both
models remain stopped; proxy/watchdog inactive. See terminal-state.txt.

This is micro qualification only. No checkpoint loaded, serving, smoke, full
speed/acceptance matrix, production adoption or TODO3 completion. A source-
reviewed compound diagnostic and separate full startup safety gate remain
necessary before backend A/B.
