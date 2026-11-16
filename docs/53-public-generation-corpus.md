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
responses and incomplete/changed receipts. Hardware execution is pending.
