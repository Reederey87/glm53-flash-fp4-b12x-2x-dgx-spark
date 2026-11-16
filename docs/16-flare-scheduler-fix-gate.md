# Prompt-latency correction — registered 2026-11-16 UTC

The user explicitly authorized production adoption, boot enablement and a
controlled reboot after qualification, and requested correction of the measured
concurrent prompt latency. No further adoption approval is required. Numerical,
long-context, loaded-shutdown and performance failures still prevent adoption.

## Isolated CPU prerequisite window

The first offline diagnostic window ended with retained exit101 before compilation.
Its no-install contract was honored. A new, separate worker CPU window may fetch
the existing pinned Cargo.lock dependencies, then run the frozen control fixture.
This changes only the Cargo download cache and isolated test artifacts, not the
preparation environment, serving binary, core, source pin or runtime settings.

Use `/home/nvidia/b12x-flare/local/scheduler-lab-20261116T005600Z`, detached at
Flare `5a4e867954593b2e05bba43bc2a6eeaddca402d7`, with fixture SHA256
`6e5ae9c07095e208dbefdf4d8bf3943004d57544491f513698c18deb5710c099`.
Require the exact recorded fixture-only diff and unchanged preparation tree.
Record Cargo.lock SHA256 before and after. Existing Rust 1.99.1 is retained.

Run `cargo fetch --locked --target aarch64-unknown-linux-gnu`, then the original
`cargo test --locked --offline --jobs 2 --features server --lib b12x_prefill_trace
-- --nocapture --test-threads=1`, both with the lab's helios manifest and an
isolated lab target directory for the test. Missing or changed lockfile fails.
Cargo's [official fetch contract](https://doc.rust-lang.org/cargo/commands/cargo-fetch.html)
supports preparing exact dependencies for subsequent offline execution. No
dependency upgrades, toolchain installs or host package changes are allowed.

Use a new retained Type=exec user unit with a 20-minute runtime bound, 30-second
stop timeout, control-group kill, CPUQuota200%, MemoryHigh6G, MemoryMax8G and
MemorySwapMax0; CUDA_VISIBLE_DEVICES is empty. Start only with inference stopped
on both hosts and at least25 minutes before the head's02:10:40 UTC restoration.
Capture actual exit status and test output before stopping the unit. Stop and
verify MainPID0 before any earlier restoration. The head's independent full-scale
audit remains unchanged. A failed prerequisite is not a scheduler test result.

## Candidate and acceptance requirements

The unchanged native control has now passed. At four32768-token prompts, both
balanced and throughput select slots0,1,2,3 repeatedly and produce first outputs
after prefill dispatches29,30,31,32. This is production-selector CPU evidence
with synthetic costs, not an on-GPU trace. The missing protoc error was resolved
by using the candidate's existing isolated build environment; no host install.

`qualification/flare-prefill-latency.patch` proposes opt-in `latency` scheduling.
For separate prefill graphs it chooses the eligible request with lowest
`arrival_time + remaining_tokens * measured_full_chunk_time / chunk_tokens`.
Equivalently, this favors less remaining service minus accumulated request age.
Shared positive measured costs keep continual new short arrivals from permanently
dominating an old request; there is no unconditional wall-clock bound under
decode overload. Unknown timing retains normal discovery. Decode and terminal
prices, graph shapes, costs, feedback barriers and refresh budgets are retained.
Mixed-prefill catalogs reject this mode rather than silently using another rule.
Balanced and throughput behavior remains unchanged.

This adopts TensorFold's remaining-work preference with the research's continuous
arrival aging instead of its fixed skipped-chunk guard. New CPU regressions cover
equal/unequal prompts, ongoing short arrivals, cancellation, unmeasured graphs;
existing decode-progress and two-in-flight feedback regressions also exercise
the new mode. CLI/config parsing is explicit. These treatment tests are pending.

After freezing the patch, run it only in the detached worker test tree under a
new retained CPU unit with the same20-minute/8GiB limits and deadline checks.
Run all `scheduler::` library tests, configuration tests, the frozen control
fixture and the CLI policy parsing test offline/locked, single test thread.
Capture test counts and failures; no skipped case is passing evidence. The
serving binary and preparation source remain unchanged until this stage passes.

First establish the unchanged selector's service order. Exa's
[upstream scheduling design](https://github.com/NVIDIA/spark-local-inference/blob/main/docs/scheduling-runtime-design.md)
retains prompt-token fairness in both presets; changing to throughput alone is
not a supported latency fix. The earlier feedback-drain starvation issue is
already addressed in pinned `policy.rs::available_plan`; do not reapply it.

Investigate a completion-oriented prompt preference with bounded waiting,
preserving decode/terminal service and captured graph geometry. Exa's
[aging/remaining-work scheduling research](https://arxiv.org/html/2606.09061v1)
motivates the tradeoff but proves no improvement on this hardware. Local vLLM
running-order scheduling and TensorFold's remaining-work selection with an
eight-skipped-chunk guard supply concrete alternatives. exllamav3's different
state/layout contracts are not a drop-in scheduler change.

Any implementation must pass native selector coverage for equal and unequal
prompts, sustained short arrivals, active ordinary/speculative decoding,
cancellation, retirement, stale cost discovery and two submissions in flight.
Retain unmodified control results. Do not tune only to the equal-length matrix.
Then freeze one native host-policy change, verify it is active, trace actual
request service and repeat the registered full matched performance matrix.
Preserve checkpoint, quantization, core, KV reservation and original numerical
bounds. A CPU simulation cannot replace native trace or hardware evidence.

After all qualification gates pass, deploy the exact qualified artifacts, smoke,
enable a single Flare cluster startup owner and bounded watchdog, and disable
conflicting B12X startup/watchdog. Preserve rollback files and image identities.
Before the controlled two-node reboot, register a persistent rollback mechanism
that survives reboot; existing transient trial timers do not. Verify new boot IDs,
both rank identities, API health, generation, startup enablement and watchdog
recovery. No driver or kernel upgrade is part of this work.
