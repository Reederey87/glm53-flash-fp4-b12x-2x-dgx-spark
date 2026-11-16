# Counterbalanced performance repetition

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
