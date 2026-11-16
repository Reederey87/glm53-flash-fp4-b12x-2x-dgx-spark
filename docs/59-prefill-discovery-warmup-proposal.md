# Candidate startup warmup for graph-cost discovery

The first completed docs/55 balanced trace has76 complete request histories,
1,129 contiguous completions, zero drops/truncation and clean native exits.
In its first unequal burst, native request(1,1) finishes4096-token prefill at
4.8624seconds but snapshots at12.1936seconds. Nine intervening discovery
operations (eight prefill sizes and initialization) account for7.3312seconds.
The corresponding HTTP cohort has only one4096-token request: TTFT1.7103seconds,
completion9.0416seconds. Native timestamps are not socket-delivery timestamps;
length/cohort correspondence does not add an HTTP identity field to the trace.
The ongoing latency arm also shows this pattern; its full trace is not yet
validated, so no paired or performance conclusion is claimed here.

Exa reviewed NVIDIA's [scheduler implementation](https://github.com/NVIDIA/flare-local-inference/blob/main/helios/src/scheduler/policy.rs),
[scheduling design](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/scheduling-runtime-design.md),
[preparation contract](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/preparation-development.md)
and [benchmark semantics](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/cli-design.md).
Pinned `utility.rs::ValueRate::compare` prioritizes unknown-duration candidates
before comparing their value against measured candidates. Increasing terminal
value alone cannot outrank that ordering. Changing terminal scheduling or moving
visible completion before snapshot publication would alter lifecycle policy and
requires separate qualification; neither is implemented here.

Preparation warmup/capture and native serving cost discovery are distinct.
A128-token API warmup does not measure the larger captured prefill sizes.
An alternative is an explicit, bounded workload before production readiness.
Local review checked vLLM's shape-specific warmup and speculative state reservation,
exllamav3's full-chunk/batch/long-context warmup schedule, TensorFold's separate
per-shape warmup and measured MTP costs, and the unchanged FlashInfer contracts.
The useful technique is covering prefill and concurrent decode shapes before
serving users, while retaining this checkpoint, quantization, core and KV pool.
No other engine or model policy is adopted.

## Prepared client, no adoption decision

`scripts/flare_warmup.py` runs exactly two passes, each containing one32768-token
request/8 outputs, two simultaneous1024-token requests/256 outputs, and four
simultaneous1024-token requests/512 outputs. T1/top-p.95, explicit ignore-EOS,
fixed seeds and14 distinct cold prompts. Exact lengths/counts and complete
streams are required. Record all timings, hashes and scheduler reason-counter
deltas. Missing/duplicated counters or resets fail. A surrounding controller
must enforce an external timeout and the existing memory/rollback protections.

Completion does not prove graph coverage or a speed improvement. Before any
startup integration, finish docs/55; freeze a separate warmup-only comparison,
retain loss-free native traces showing which prefill/speculative shapes were
measured before the probe, and measure startup overhead plus post-warm response
behavior. Cold-prefix guarantees remain; useful output, state, memory, capacity
and full performance gates remain unchanged. If subsequent performance testing
uses warmup, both policy arms must receive exactly the same fixed warmup and
all prior failed measurements remain retained. Do not repeat until favorable.

Local syntax, strict counter/reset checks and distinct-prefix checks pass.
The client is local only and unrun; no startup entry point invokes it. This
proposal addresses the observed cold-discovery delay, not all10 unresolved
ABBA points. Broader graph warmup must earn adoption through new evidence.
