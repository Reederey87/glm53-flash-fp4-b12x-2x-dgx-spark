# Diagnose the unresolved ABBA points

> Historical architecture or qualification record. Current production, unresolved gates and the research pause: [docs/63](63-production-pause-checkpoint.md). Old window controllers must be adapted before reuse.

Docs/50 did not pass its registered gate. Do not repeat until favorable, discard
the adverse points or substitute traced timings for performance qualification.
The next window observes the same workload bodies, budgets and three repetitions
with the existing native binary. It changes no scheduling or model code.

Exa reviewed the primary [scheduling lifecycle](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/scheduling-runtime-design.md),
[native scheduler contract](https://github.com/NVIDIA/flare-local-inference/blob/main/helios/README.md),
[feedback-window starvation issue](https://github.com/NVIDIA/flare-local-inference/issues/42)
and [CLI benchmark contract](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/cli-design.md).
Terminal snapshots compete for service independently of output publication;
feedback-dependent work must remain selectable before draining the submission
window. Pinned local source already contains the feedback-starvation correction
and tests; the issue is not evidence that this candidate still has that bug.
Repeated snapshots/restored GPU rounds are useful component diagnostics, but
exclude the HTTP scheduler and cannot replace this end-to-end comparison.

Local review covered native cohort selection, terminal publication, graph-cost
discovery/refresh and observer bounds; vLLM running-request/token budgets;
exllamav3's separate shared-prefill chunk limit; TensorFold's bounded bypass and
decode-aware scheduling; and the unchanged FlashInfer operator contracts reviewed
in docs/26. Possible stronger treatments include preserving baseline selection
for already-small prompts, decode-aware chunk caps or terminal-service tuning.
Each requires an observed mechanism, separate frozen treatment and fresh gates.
None is implemented here. Decoupling terminal delivery must preserve fenced
ownership and immediate-continuation cache publication.

## Frozen diagnostic window

`abba-trace-window-20261117T020000Z` starts only after independent MTP-replay
window recovery and fallback disarm. Keep binaryb2eb310b/native127424e9,
coredf214696, wrapper41b65a5a, TP2/four slots/MTP3/chunk4096/CP-off/reserve4.
Use run identity `performance-abba-20261116`, unchanged temperature1/top-p.95,
sampling seeds, exact cold prompts and output budgets.

Four fresh starts: balanced mixed, latency mixed, latency long-output, balanced
long-output. Each mixed start runs all75 requests; each long-output start runs
all12. Each client warms once, with the same128-token warmup as before. The
existing observer is bounded to600seconds,16MiB and16,384 completions. Separate
workload starts preserve these bounds without rebuilding the observer. The
previous mixed suites took561–563s and long-output suites330–349s; use a580s
external client deadline and require a clean stopped trace footer. A timeout,
duration-ended trace, dropped update, missing fence/history or bound truncation
invalidates the diagnosis and restores B12X. No partial trace is accepted.

Verify both actual native identities and head-only tracing before each client.
Health readiness and client warmup are used here; extra API smoke traffic would
contaminate the expected native histories. Prior API smoke remains separate.
Separating workloads into fresh starts and omitting that API traffic changes
graph-cost history relative to docs/50. These traces can expose a mechanism if
the delay recurs; they cannot prove the cause of an earlier unobserved delay or
establish performance equivalence merely because it does not recur.
Require76 complete cold prompt histories per mixed arm and13 per long-output
arm, exact prompt-length multisets, contiguous native fences, zero drops, real
both-rank exit0 and no forced kill. Retain selected/commit/completion times,
GPU/wall graph durations, timing origins, native request generations and all
state-operation events. Native generation IDs are not HTTP IDs. Graph-completion
gaps are not streamed-token gaps; terminal cause needs matching event evidence.

Keep one continuous notifying memory guard across all four starts with the
original1.5GiB-free/8GiB-available floors and idle gates between starts. Controller
80minutes, guard85minutes, independent rollback90minutes. Restore the original
B12X images on completion or error; independently verify API/watchdog/tailnet,
absent native processes and fresh5/5 smoke before disarming fallback.

The analyzer reproduces the retained loss-free414/405-completion traces and
rejects injected loss and missing prompt histories. These are local validator
checks; this new GPU window is unrun. Its diagnostic receipt cannot qualify
production or unlock the full84-row/capacity gates by itself.

The frozen trace window started after independent10:12:07 UTC B12X recovery.
Controllerdde3853b1159467f94ba7ee25d12a3e8; notifying memory guard
f0f471d37c144fd79443bdf1ef8789b8;90-minute fallback armed. Results pending.

All four diagnostic arms completed:178 histories/5,394 contiguous completions,
zero trace loss/truncation, eight clean native exits and411 healthy memory samples.
Detailed findings/limits are in docs/60. This passes diagnostic integrity only;
performance remains unqualified. Independent B12X restoration is underway.
