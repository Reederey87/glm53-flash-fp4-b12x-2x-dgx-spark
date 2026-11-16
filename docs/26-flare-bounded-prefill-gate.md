# Bounded prefill correction — native diagnosis and registered gate

> Historical architecture or qualification record. Current production, unresolved gates and the research pause: [docs/63](63-production-pause-checkpoint.md). Old window controllers must be adapted before reuse.

## Complete mixed native evidence

Observer artifactde4c3f7c completed both arms with zero dropped updates,
truncation or missing fences. Each matches25 original rep0 request bodies,
26 contiguous prompt histories including warmup, and360658 prompt tokens.
Balanced414 completions/37 memory samples; latency402/36. Both ranks exited0
without forced kill after each arm. Raw traces, client rows, identities and
analysis are `mixed-observer-*` in receipts/flare-qualification-20261115.
`qualification/analyze_mixed_trace.py` reproduces the analysis and rejects the
retained dropped-update trace. Native generations are not asserted to be HTTP IDs.

Balanced's largest native decode-completion gap was1.144672s: ordinary
prefill1024 GPU0.693799s, refresh prefill2560.355969s, then speculative2x4
0.092895s. Client gaps were1.14450/1.14453s. Latency instead selected ordinary
prefill3072 steps taking1.375901/1.432680s, followed by speculative decoding;
native gaps1.474604/1.501272s closely match client1.47487/1.50090s. These were
measured ordinary shapes, not unknown-cost discovery. One large step followed
completion of the short4096 prompt while the long32768 prompt had received no
service; another followed one decoder's retirement. Changing cohort selection
therefore changed graph competition despite unchanged decode price coefficients.

The prior36s late-short failure did not recur: this traced pair measured
1.6670s balanced versus2.2632s latency for short15. Do not claim this capture
proves that earlier failure's cause. Its three-repetition untraced failure stays
retained. A separate CPU counterexample must establish the unbounded arrival-age
rule's ability to delay short work before claiming that mechanism is corrected.
Neither traced result substitutes for the untraced performance gate.

## Exa and source-qualified proposal

Exa rechecked [QBA paper](https://arxiv.org/abs/2610.17795) and
[implementation](https://github.com/Julianjiuxi/qba-llm-serving). Unrestricted
aging can over-promote old long work; bounded promotion earns quota on completed
short prefills rather than chunk continuations. Its reported evidence is
simulation/production-trace replay, not this hardware. Our proposal is not the
paper's prediction/quantile/debt algorithm and does not inherit its measured gains.
[SLOWeave](https://arxiv.org/pdf/2609.07883) remains a stronger, separate option
for deadline-aware chunk sizing, conditional on predictor accuracy and feasible
decode load. No universal wall-clock guarantee is claimed under overload.

After lookup, re-read pinned Flare cohort/value selection and completion
accounting, local vLLM running-request/token budgets, exllamav3's bounded uncached
forward chunks, TensorFold's shortest-remaining selection with bounded bypass
and decode round credit, and FlashInfer's immutable A16/A4 binding contracts.
The TensorFold technique informs bounded bypass here; adopting its server or
changing quantization, kernels or KV layout is outside this candidate.

The new latency preset has two explicit rules within one scheduler treatment:

- While any decoder/resume is live, retain balanced prefill cohort selection,
  including its graph-value competition. Do not merely retain price constants.
- Otherwise prefer shortest remaining prefill. After eight other successful
  prompt completions since a request last made prefill progress, promote it for
  one chunk. Successful progress clears that request's saturating counter.
  Count actual prompt crossings once, not planning calls, chunks, errors,
  snapshots or decode events. Reused slots start at zero. Overdue requests are
  ordered by last progress, then arrival/slot; ordinary ties use arrival/slot.

Unknown-cost discovery, graph prices, feedback, continuation and separate-graph
restrictions remain. The bypass bound applies to eligible prompt selection,
not arbitrary decode overload or requests awaiting admission. The quota8 is a
preselected guard, not a value tuned after hardware numbers. The candidate is
unqualified until CPU and live gates pass. Gains with nontrivial output budgets
may be smaller than max1 probes because balanced behavior resumes during decode;
check a matched long-prompt/output workload before adoption.

## Registered CPU control and build

Keep original age policy bytes in `flare-prefill-latency-age-control.patch`
(SHA338bbeb0). A fresh worker control worktree applies those bytes and the shared
mixed regression fixtures. Require a genuine late-short assertion failure,
not a compiler error. The active-decode same-state comparison may also fail;
retain its actual outcome. No other existing test may fail. This expected
counterexample is an explicit control, not an unexpected failed serving gate.

The candidate in a separate fresh worktree must pass both new regressions,
completed-prompt/reset and cancellation/slot-reuse tests, all prior scheduler
checks, observer/dashboard, config and CLI tests, then release build. Preserve
both Cargo locks and capture actual terminal status and manifest/binary hashes.
The builder is `qualification/build_bounded_scheduler.sh`; it runs CPU tests
with no CUDA execution, two compile jobs and the original idle-memory gate.
Local launcher/client checks66 pass; native candidate tests are still pending.

## Hardware window and decisions

Window `bounded-window-20261116T041500Z`; pre-arm180-minute restoration before
stopping B12X. Snapshot both ledgers, images, runtime hashes and unit ownership.
The helper must stop this window's exact worker build, head clients and memory
watch before restoring through the original B12X unit. Require90GiB free and
100GiB available on both nodes before build/start; enforce1.5GiB free/8GiB
available while serving. Unexpected build/test/health/memory failures restore.

Freeze the candidate commit first. After build, stage immutable artifact files
atomically and validate hashes and actual launcher/provenance commands before
starting either rank. Do not dynamically discover an unchecked artifact after
production stop. Use the same new binary for balanced and bounded latency,
core df214696, checkpoint76348ddb, TP2,4slots,MTP3,chunk4096,CP-off,reserve4,T1/.95.
Trace is off for every performance measurement. No boot or host upgrades.

1. Fresh balanced start, exact argv/binary/core identity,7-check API smoke and
   the full three-rep75-request mixed control. Retain actual exits on transition.
2. Fresh bounded latency start with identical controls, API smoke, same75
   requests and strict comparator. Reject any separated >2% regression; an
   overlapping bad median needs investigation/repetition, never automatic pass.
3. Only if mixed passes, run the full84-row/315-request-hash matrix against the
   retained B12X reference, with every per-request TTFT and decode/acceptance
   metric. Aggregate throughput cannot conceal a failed point.
4. Pass loaded graceful shutdown and peer-loss qualification with actual
   invocation-bound exits and guarded restoration. Numerical, long-context,
   state reuse, capacity and production ownership gates in docs/23 remain.

Restore on any failed serving gate or deadline. After the window verify original
B12X images, health200, fresh5/5 smoke and watchdog/tailnet, append rollback
selection and only then disarm fallback. No adoption/merge based on these
partial results. Production adoption and main/GitHub delivery remain authorized
once the best candidate satisfies the complete qualification requirements.

## Build provenance correction and reproducible window

The build invocation transcribed the source commit suffix incorrectly. The
frozen source is `0c8f805fae82b768591fc908a936a7efec672234`; its policy patch
SHA is `ef027822eb59345165212b43706a181154ba67e7a75079e7e51f1ef73c6177b4`.
Reject the incorrectly attributed manifest before any serving. Preserve it,
verify all four inputs against bytes read directly with `git show` from the
frozen commit, verify the native build terminal status, dependency locks and
binary digest, and publish a new immutable manifest recording the correction.
This changes provenance only; no new compilation or claimed test result.
[Official SLSA guidance](https://slsa.dev/spec/v1.2/build-requirements) informed
this separation of output identity and source provenance; this local process
is not claimed to be a SLSA-certified build platform.

Exact window helpers are retained in `qualification/windows/bounded-20261116/`.
They use the registered fallback and memory gates. The serving helper rejects
any unresolved mixed comparison point before the full matrix is started.
