# Passive startup memory observation

Pre-registered before restart. This is a diagnostic dependency of candidate3,
whose b12x arm has never run. No inference optimization or adoption decision is
made from this observation. Final independent code review precedes staging.

Independent variable: passive per-module startup snapshots only, installed via
the pinned launcher's supported mods hook into both fresh containers. The patch
refuses a loader source other than SHA256 `aa398e74ee835537403e60186f2e9a81e8741a4b35fec68b47df6537716a45b7`.
It logs module name/type, worker PID, wall/monotonic timestamps, allocated,
reserved, releasable, peak allocated, integrated-device flag and host memory.
It records the existing pressure helper's actual result without altering its
conditions or call frequency. No added synchronization, clearing, GC, tensor
inspection, allocator limit, packing, dtype or kernel change.

Frozen: image `3b5da79c`, checkpoint `76348ddb`, TP2, Humming draft MTP3,
target b12x/B12X, four seats, context1M, batch4096,17G FP8 KV/pool2,350,210,
default allocator, original drivers/kernel/cache policy and launch command.
Only `mods:` differs in the observation recipe; the canonical recipe stays
untouched. `WINDOW_KIND=observation` runs one arm; it never fabricates a paired
performance comparison. Recovery explicitly selects the canonical recipe,
not the traced one, and creates fresh containers from the unchanged image.

Evidence gate: both actual rank/image profiles; each rank's exact patched-loader
and helper hashes embedded in the trace; ordered per-module before/after/release
triples with the actual boolean helper result, and model/attention boundaries.
Retain the last completed phase if aborted. The integrated-device flag is an
observation (including false), not an assumed value. A fully healthy
boot additionally requires both Humming resolved-kernel markers, exact KV pool,
smoke5/5, parity and the same20cold-prefill/12post-ladder decode matrix. These
are operational checks, not proof of a speedup from observation overhead.

Safety: independent host observer with unchanged2GiB MemAvailable floor during
observation **and recovery**, matching InvocationID and<=20s heartbeat. A
recovery safety abort is terminal; no automatic reset/retry of that boot. The
proxy stays closed if restoration cannot pass its image/profile/smoke/health/
unit and observer checks. No driver/kernel updates or reduced KV permitted.
An EXIT cleanup handles failures inside shell functions. Blocking recovery
commands are supervised with bounded observer polling. Before reopening access,
stop/join the observer, require inactive/dead + success/status0, reconcile the
abort marker, and verify live health. Both restored loader hashes must match
the original untraced image. A single-arm validator emits no paired result.
All exits restore canonical RECIPE/default allocator through the unit and append
the ledger; `ExecStopPost` recovers interruption. Single-use output directory:
`local/ab-startup-memory`; preserve the earlier failed draft output.

Research first: Exa lookup of upstream
[cache release45179](https://github.com/vllm-project/vllm/pull/45179),
[same-checkpoint post-load report441](https://github.com/eugr/spark-vllm-docker/issues/441),
and stronger [UMA allocator cap49760](https://github.com/vllm-project/vllm/pull/49760).
The installed image already includes45179's hook.49760 is an open, profiling
budget proposal; its small-model result does not identify this post-load peak.
AllocatorTrue was previously unsafe at our frozen17G; it is not retried here.

Local vLLM/installed model loader and ModelOpt/b12x preparation reviewed; current
source differs from installed bytes, so the patch is pinned to actual runtime.
EXL3 frees unreferenced cache; FlashInfer preparation owns packed-storage and
scratch lifetimes; Flare tracks allocated/reserved and transient preparation
pools. TensorFold bounds in-flight layers with CUDA events and periodically
releases cache. Adopt its phase/budget receipts in this diagnostic; defer any
new barrier/pool/allocator policy to a separate measured treatment after traces
identify the phase. No alternate engine or weight format is introduced.

Recovery review follow-up also consulted Exa results for the
[Bash manual](https://man7.org/linux/man-pages/man1/bash.1.html) and
[systemd service lifecycle](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html).
Use EXIT cleanup rather than relying on ERR inheritance; reconcile terminal
observer evidence because a completed stop command alone does not prove health.
