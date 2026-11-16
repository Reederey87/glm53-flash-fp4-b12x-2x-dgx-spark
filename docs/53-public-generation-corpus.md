# Public generation and semantic comparison

Component references and native replay do not establish useful exported-model
behavior. `scripts/flare_generation.py` freezes50 public cases:20 short chat,
10 forced tool calls,10 constrained JSON answers and10 long-passage retrievals.
Each engine receives identical bodies, explicitT1/top-p.95/seed531716 and Low
reasoning. The existing seven-check smoke separately verifies omitted effort=Max.
No thinking cap or unsupported greedy setting is added to either engine.

Exa MCP reviewed [Flare's generation acceptance](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/core-design.md),
[speculative benchmark semantics](https://github.com/NVIDIA/flare-local-inference/blob/main/qualify/speculative_benchmark.py)
and [native API contracts](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/api.md).
The upstream speculative corpus targets a different model/EOS set and is not
copied as a GLM fixture. Its separation of complete answers from budget-exhausted
outputs is retained. Pinned local review covered Flare's GLM template/API,
vLLM's GLM MTP and request sampling, exllamav3 feedback semantics and TensorFold's
explicit input/reference contracts. A common seed does not make different
engines' stochastic streams identical; this test does not assert token equality.

## Preregistered protocol and interpretation

For every case, run one64-token-budget generation probe and then a separate
1024-token-budget semantic request, in that fixed order. Do this for all50 cases,
not only failures. Both engines receive all100 requests. A short probe ending
at its token budget is retained as truncated, never counted as a completed
answer. The longer phase provides enough room for the model's reasoning and
answer; it does not replace or relabel the64-token evidence.

Every response must have the correct model, one assistant choice, valid positive
usage within its requested budget, nonempty output and a recognized terminal
reason. All50 longer answers must satisfy their frozen objective expectation
without exhausting the budget: exact short answer after stated whitespace/case/
outer punctuation normalization, exact tool name and JSON arguments, or exact
typed JSON object. The long cases copy an unambiguous code from a public passage.
Record actual prompt counts; filler repetitions are not exact tokenizer lengths.

Store complete public responses, response/request hashes and both phase verdicts.
The validator reconstructs every body and verdict and rejects missing, duplicated
or changed rows. Compare only matched run IDs and complete100-request receipts.
Both engines must pass all structural checks and all50 semantic answers for this
gate. A failure requires diagnosis; a baseline failure is not automatically a
Flare defect, and neither engine's failure is silently waived. Preserve the
64-token truncation list in the final comparison. This is functional/semantic
evidence, not full-vocabulary numerical equivalence or a throughput benchmark.

Run only inside a later guarded serving window, with frozen selected artifact,
memory enforcement and rollback; never overlap the ABBA performance measurement.
State transfer, concurrent retrieval, capacity and full speed gates remain
independent. Four focused tests pass for truncation, typed answers, malformed
responses and incomplete/changed receipts. Hardware execution was interrupted at the user’s research pause; see the outcome below.

## Frozen serving controller

`generation-window-20261117T060000Z` runs only after the successful docs/58 MTP
gate and independent B12X recovery. Exa rechecked the NVIDIA model card and
Flare core acceptance; the card validates vLLM, so Flare qualification remains
separate. Its template supports Low/High/Max reasoning and defaults to Max.
The existing fixtures and verdicts remain unchanged.

Run all100 baseline requests on the original B12X image, then all100 candidate
requests on native127424e9/coredf214696 with bounded latency/reserve4/trace-off.
All request bodies/settings match; seeded cross-engine token equality is not
asserted. Verify both native ranks, API7/7, full receipt comparison, both clean
native exits and continuous candidate memory samples. Preserve both complete
public-response sets even if a semantic verdict fails. This is a functional
comparison, not an A/B speed experiment or a substitute for capacity qualification.

Each client has an external60-minute timeout and30-second kill grace; controller
130minutes, memory guard135minutes, fallback150minutes. The guard starts after
baseline teardown and before candidate load; the original B12X service owns the
baseline. Restoration always returns to B12X, independently verifies both images,
API/watchdog/tailnet and fresh5/5, then closes fallback. Controller/manifests are
were executed without production ownership changes; the user stopped research before the candidate client finished.

## Paused outcome — 2026-11-16

Research stopped at the user's request at 11:21:29 UTC. The baseline completed
100/100 responses; the candidate completed 86/100. All completed responses passed
the structural checks. Baseline semantic failures were chat-07, chat-11, chat-16
and chat-17; the partial candidate failed chat-16. The first two baseline failures
include extra text, chat-16 gives B instead of D, and chat-17 refuses the public
copy task. These observations do not establish an engine-specific root cause.
All ten baseline long cases passed, reaching 213,041 actual prompt tokens.

The full paired gate is **incomplete**, not passed. No comparison of partial
counts is a quality improvement claim. Complete public responses, hashes,
individual verdicts, candidate API7/7, identities and memory samples survive as
`receipts/flare-qualification-20261115/generation-paused-*`. B12X restoration
independently passed fresh5/5 and closed at 11:28:11 UTC. Restart qualification
in a new window after updating ownership/rollback for the production checkpoint
in [docs/63](63-production-pause-checkpoint.md). Do not resume this controller.
