# Counterbalanced performance repetition

> Historical architecture or qualification record. Current production, unresolved gates and the research pause: [docs/63](63-production-pause-checkpoint.md). Old window controllers must be adapted before reuse.

Docs/32 and40 retain adverse overlapping medians; docs/36's trace explains
some arrival-phase effects without resolving the performance gate. The next
experiment repeats both complete workloads with fresh balanced, latency,
latency, balanced starts (ABBA). It changes only scheduler policy. It does not
discard previous results, alter prompts/output budgets, or treat overlap as a pass.

Exa MCP reviewed the primary [ordering-trap study](https://par.nsf.gov/servlets/purl/10436963),
[NIST blocking guidance](https://www.itl.nist.gov/div898/handbook/pri/section3/pri332.htm)
and [Flare benchmark/CLI contract](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/cli-design.md).
Ordering and carryover can bias grouped A-then-B trials. Local review covered
Flare graph selection/completion accounting, vLLM scheduled-token and benchmark
controls, exllamav3 separate prompt/decode chunk limits, FlashInfer's fixed
projection contracts, and TensorFold's fresh-process ABBA driver. Adopt its
counterbalanced fresh-start technique here, preserving quantization and KV settings;
do not adopt its unrelated model thresholds, server or global cache dropping.

A stronger experiment uses multiple independently randomized blocks and a
preselected uncertainty model. This single ABBA block supplies two starts per
policy and six observations per request role, not six independent starts or a
statistical confidence claim. It is the next fixed repetition of the existing
descriptive gate, not an open-ended repeat-until-pass loop.

## Preregistered protocol

Window `performance-abba-window-20261116T220000Z`, after independent docs/49
recovery. Freeze native127424e9/binaryb2eb310b/coredf214696, wrapper41b65a5a,
checkpoint76348ddb, TP2/four slots/MTP3/chunk4096/CP-off/reserve4, trace-off,
T1/.95 and omitted reasoning=Max. No capacity tuning in this window.

Run exactly four fresh starts in the registered order. At each, verify both
native invocations and frozen identities, API7/7, observed pool capacity, then
the unchanged three-repetition75-request mixed suite and12-request fixed256-output
suite. All four starts use the same new run identity, producing identical bodies
within each workload. Fresh processes remove prefix/cache state; existing clients
warm once and require measured cold-cache counts. Both ranks must exit0 without
forced kill before the next start. Do not stop after favorable interim numbers.

Keep one continuous notifying memory guard from before first load through final
teardown, with the unchanged1.5GiB free/8GiB available floors and idle gates on
every transition. Stop the guard only when restoring B12X; its OnFailure path
may queue that same idempotent restore. The controller limit is110minutes,
guard115minutes, fallback120minutes. An idle/identity/API/memory/client/exit
failure stops the window and restores B12X. No next arm starts after such failure.

## Analysis and decision

Validate all four complete receipts and distinct native invocation IDs on both
nodes. Report forward A0/B1 and reverse A3/B2 comparisons separately, then combine
their six retained observations per policy. Preserve every original61 mixed and17
long-output timing point, plus long-output mean acceptance length
`1+accepted/drafts` and draft acceptance rate `accepted/draft_tokens`, using
validated per-run counter deltas. Stream delivery gaps remain delivery gaps,
not inferred per-token latency.

The repeat gate requires no combined median regression over2% at any of80 points
and no separated regression over2% in either order-specific pair. Any adverse
overlapping combined median stays unresolved. A disagreement by ordering stays
visible in the report for review; no automatic adoption follows this gate.
All earlier results stay retained. Only after this evidence resolves mixed and
long-output performance may the full84-row comparison proceed. Capacity,
numerical/MTP, context/state and production recovery gates remain independent.

Restore B12X at window completion regardless of the descriptive result. Require
both original images, API/watchdog/tailnet, absent native processes and fresh5/5
smoke before fallback disarm. No production boot ownership changes here.

The frozen controller started08:26:28 UTC after docs/49 recovery closed, invocation
`fb7139ba1ca54aec93e8ce59f6e0ee8c`. Both ledgers/hashes and original images were
snapshotted; the120-minute fallback is armed. No performance result yet.

Additional Exa methodological review during the running window covered
[effect-size confidence intervals](https://arxiv.org/pdf/2007.10899) and
[randomized multiple interleaved trials](https://dl.acm.org/doi/10.1145/3030207.3030229).
They reinforce the distinction between iterations within a start and independent
starts, and between uncertainty in a ratio and a single point estimate. They do
not turn overlapping ranges or a nonsignificant difference into equivalence.
Any later statistical design needs a fixed replication plan, chosen effect
threshold and uncertainty method before its measurements. The present80-point
ABBA gate, its thresholds and all four required starts remain unchanged.

Exa also checked the primary [scheduler lifecycle design](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/scheduling-runtime-design.md)
against the pinned local scheduler and terminal-snapshot tests. Response completion
waits for terminal snapshot/cache publication; terminal retirement competes with
inference using its own value and age. Graph-cost discovery and stale-cost refresh
are separate mechanisms. These explain why TTFT, last output and response completion
must be retained separately. They do not identify the cause of any measured delay
without a matching native trace. Changing retirement priority or decoupling response
completion would require a separate lifecycle-qualified treatment, preserving fenced
resource ownership and immediate-continuation cache semantics. No such change is
included in this ABBA window.

## Complete result — gate not passed

All four starts completed by09:35 UTC:348 measured requests, four7/7 smokes,
distinct native invocations and actual exit0 on both ranks without forced kill.
All754 memory observations were healthy. Minimum free/available GiB were
1.735/10.487 on the head and1.726/11.144 on the worker. Pools were2,335,232
tokens for starts0–2 and2,331,392 for start3; reserve remained4GiB. The independent
2,350,210-token capacity requirement remains unmet.

The registered80-point comparator reports70 points without an adverse combined
median over2%,10 unresolved adverse combined medians, and zero separated>2%
regressions in either order-specific pair. `repeat_gate_passed=false`.

| Workload / request | Metric | Combined median change |
| --- | --- | ---: |
| Decode overlap / decode0 | p95 delivery gap | +3.35% |
| Decode overlap / decode1 | amortized decode rate | −4.10% |
| Decode overlap / decode1 | completion rate | −5.91% |
| Decode overlap / decode1 | elapsed | +6.26% |
| Decode overlap / decode1 | TTFT | +13.16% |
| Unequal burst / request3 | elapsed | +4.48% |
| Long output /32k | maximum delivery gap | +9.89% |
| Long output /8k | elapsed | +10.52% |
| Long output /8k | maximum delivery gap | +14.16% |
| Long output /4k | elapsed | +2.33% |

Retain all observations; no favorable subset or overlapping range qualifies
this candidate. Identical request bodies/seeds produced different output hashes
across fresh runs, including within each policy. That is an observed source of
workload variation, not proof of the cause or permission to discard timings.
Matching native traces are still needed before any further scheduler change.
Full84-row and capacity windows remain gated. Numerical qualification can proceed
independently after verified B12X restoration. Receipts: `performance-abba-*`.

Independent B12X recovery closed09:40:08 UTC: original images on both nodes,
API200, watchdog/tailnet active, absent native processes and fresh5/5 smoke.
Restore invocationb7b722eb44f24fb286980c49f8d322b0 and smoke
acdb9aa1737b416fa2d4fa5821a0ef42 ended with actual exit0/PID0.
Fallback was disarmed only after independent verification.
