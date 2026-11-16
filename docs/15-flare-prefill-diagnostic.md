# Native scheduler CPU diagnostic — registered 2026-11-16 UTC

> Historical architecture or qualification record. Current production, unresolved gates and the research pause: [docs/63](63-production-pause-checkpoint.md). Old window controllers must be adapted before reuse.

The completed hardware matrix shows concurrent TTFT regression despite similar
aggregate prompt throughput. Exa's [official scheduler design](https://github.com/NVIDIA/spark-local-inference/blob/main/docs/scheduling-runtime-design.md)
describes token-service fairness; the throughput preset retains it. The pinned
`PolicyConfig::throughput` only removes delivery fairness and decode-age prices.
The source therefore suggests interleaved prefill progress, but neither this
reading nor a simulation proves causality in the two-host native runtime.

`qualification/flare_prefill_trace.rs` runs the real production selector using
the pinned `policy_tests::interactive_engine` synthetic costs and completion
records. It compares balanced/throughput at one, two and four active requests,
32768 tokens each, 4096-token chunks, one output token, ordinary graphs and one
in-flight submission. Require complete prompt consumption, every request's first
output and retirement, and compare the service sequence before the first output.
The diagnostic prints request-slot order, consumed counts, synthetic times and
dispatch counts; it never initializes CUDA or prints prompt contents.

This is not the deployed TP2/MTP3 execution geometry, a GPU throughput benchmark,
or proof that changing fairness improves the live workload. Do not interpret its
synthetic time as measured latency. It tests whether the two existing presets
differ in pure-prefill selection before choosing a policy change. The local
vLLM running-request budget loop, exllamav3 prompt/state ownership and TensorFold
shortest-remaining-work selection with an eight-skipped-chunk guard were reviewed
as alternatives. A future preference must preserve decode progress, cancellation,
retirement and bounded prompt progress, then pass the full hardware gate.

## Isolated worker execution

The Mac has no Rust toolchain, and pinned `eos/src/unix.rs` uses Linux-only APIs.
Do not port the engine or install a Mac compiler merely for this diagnostic.
Use the idle worker's existing Rust 1.99.1 in a separate detached worktree under
`/home/nvidia/b12x-flare/local/`. Preserve the pinned preparation tree, serving
binary, accepted core and all runtime configuration. No serving launch or GPU test.

Freeze this fixture in the kit before staging. Create the detached worktree at
Flare `5a4e867954593b2e05bba43bc2a6eeaddca402d7`. Before adding the child module,
require an otherwise clean tracked tree and policy_tests.rs SHA256
`a831df8d7ad80e386f72359ead3a75f0dd0000c24308e5dc843f7e62d672d539`.
Copy the fixture as `helios/src/scheduler/b12x_prefill_trace.rs`, then append only
`#[path = "b12x_prefill_trace.rs"] mod b12x_prefill_trace;` to policy_tests.rs.
Record the fixture hash and exact resulting diff; no selector code changes.

Run `cargo test --locked --offline --jobs 2 --manifest-path LAB/helios/Cargo.toml
--features server --lib b12x_prefill_trace -- --nocapture --test-threads=1` with an isolated
`--target-dir LAB/target`. Missing cached dependencies fail the run; do not
install or update them in this window. Use CUDA_VISIBLE_DEVICES empty, a retained
Type=exec user unit, RuntimeMaxSec=1200, TimeoutStopSec=30, KillMode=control-group,
CPUQuota=200%, MemoryHigh=6G, MemoryMax=8G and MemorySwapMax=0. Verify the effective limits.

The head's full CPU scale audit may continue independently. Start this worker
diagnostic only while both inference runtimes are stopped and at least 25 minutes
remain before the head's scheduled restoration. Its 20-minute hard bound must
finish before that timer. Before any earlier manual restoration, stop the exact
worker diagnostic unit and confirm MainPID=0; do not overlap a compiler/test with
the B12X start. Record retained loaded/exited state and actual main-process status
before stopping the unit. On diagnostic failure preserve the output and leave the
head audit undisturbed; no engine or configuration has been changed.

The [official systemd-run contract](https://freedesktop.org/software/systemd/man/latest/systemd-run.html)
supports retained completion evidence. The upstream scheduler documentation
explicitly identifies these native selector tests as runnable without a GPU.
The [Cargo test contract](https://doc.rust-lang.org/cargo/commands/cargo-test.html)
defines locked/offline dependency behavior, isolated target directories and
separate build/test thread limits. [systemd resource controls](https://freedesktop.org/software/systemd/man/latest/systemd.resource-control.html)
bound this unit's CPU, memory and swap; these are not host-wide settings.
The hardware prefill regression remains open regardless of a diagnostic pass.

## First attempt: dependency preparation failed

The frozen fixture at kit commit `cfa5b721bcb4694711f27043b5c2d603bd7c4abc`
was staged in a detached worker worktree. The retained unit exited at
2026-11-16 00:54:25 UTC with main-process status 101: the offline registry lacks
`rcgen`, required by the `flare-selene-manager` test dependency. Compilation and
the diagnostic did not run. There are no scheduler trace results to interpret.

The unit's actual loaded/failed state, exit code and resource limits are retained
in `receipts/flare-qualification-20261115/scheduler-prefill-terminal.txt`; its
log and unchanged preparation-source hash are adjacent. The unit was stopped
and MainPID=0 verified. No dependency was installed and no serving file changed.
The head's independent scale audit continued.

For a future separately registered attempt, [Cargo's fetch contract](https://doc.rust-lang.org/cargo/commands/cargo-fetch.html)
supports fetching the existing lockfile's dependencies before an offline test.
Use `cargo fetch --locked --target aarch64-unknown-linux-gnu` in the isolated
worktree, verify Cargo.lock unchanged, then repeat the bounded offline test.
Do not remove test dependencies or alter the lockfile to bypass this failure.
Dependency preparation and the test rerun remain open.
