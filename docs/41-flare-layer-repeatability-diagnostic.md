# Layer output mismatch: matched-state repeatability diagnostic

The docs/39 gate failed on both ranks at layer3/decode2 after all three layer0
cases passed. Each reports2192/32768 values outside rtol0.01/atol0.001,
maximum absolute difference0.015625. State, cross-rank output equality, routing
and recorded intermediate assertions passed before the final output assertion.
The complete-layer gate therefore fails; passing subsets do not qualify it.

Exa reviewed [native numerical contracts](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/core-design.md),
[design review](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/design-review.md),
and [expert scale preparation](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/tp-checkpoint-layout.md).
They require matched operands and measured repeatability for arrival-ordered
atomic reductions. Pinned decoder/MoE paths leave routed output, shared addition,
MLP reduction and final post-mixing to investigate after the observed stages.
Reviewed local FlashInfer reduction selection, vLLM FlashInfer MoE adapter,
exllamav3 shared-expert scheduling tests and TensorFold GLM shape-dependent
arithmetic. FlashInfer's generic deterministic environment option explicitly
returns false for W4A16; toggling it blindly would not prove a treatment.

Before any serving change, replay the same prepared layer and captured graph
from identical persistent state six times in order eager/native/native/eager/
eager/native. Retain exact hashes on both ranks, finite checks, original-bound
mismatch counts, maximum absolute differences and diagnostic relative L2.
Compare each with the original eager/native result and first same-path result.
No capture instrumentation, kernel, selected tactic, precision, input or
reference change. The diagnostic runs after original intermediate assertions
and before the unchanged final output assertion. Restore original output/state
after the diagnostic. Full upstream-method AST comparison permits only the
previous documented host adaptation and this post-replay observation call.
The original numerical assertion remains mandatory and may still fail.

This distinguishes repeatability from a systematic eager/native discrepancy;
it cannot identify the specific operator by itself. If needed, subsequent
matched-operand operator probes must locate the first differing computation.
A deterministic kernel or compilation change requires its own researched,
frozen candidate, re-export when applicable and original numerical bounds.
No tolerance is widened and no performance claim follows this diagnostic.

Register `layer-repeatability-window-20261116T110000Z` only after docs/40's
window independently restores B12X and disarms fallback. Use the existing
private extension on both nodes, local GPU0/global ranks0/1 and TCP29677.
Retain docs/39's90-minute fallback,4500-second controller,3900-second rank
limits, idle/memory guards and unchanged runtime hashes. Each rank must retain
one complete six-observation diagnostic and its actual pytest status (0 or1);
controller completion means evidence collected, never numerical acceptance.
On either error, restore; independently require both B12X original images,
fresh5/5 smoke, API/watchdog/tailnet and no test/native processes before closure.
