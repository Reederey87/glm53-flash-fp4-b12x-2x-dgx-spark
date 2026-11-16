# Checkpoint MTP feedback reference

The complete target and vocabulary gates do not exercise the draft layer's
embedding/hidden feedback arithmetic. This isolated gate covers the unchanged
first nine statements of pinned `PreparedMTP.__call__`: embedding and position
masking, the two input RMSNorms, concatenation, BF16 projection and input RMSNorm.
The fixture verifies that prefix's AST and source hash before GPU work. It adds
diagnostic returns; it does not change the deployed model or export a new core.

Exa MCP reviewed [Flare's MTP implementation](https://github.com/NVIDIA/flare-local-inference/blob/main/ignition/recipes/glm53/mtp.py),
[accepted-prefix test](https://github.com/NVIDIA/flare-local-inference/blob/main/tests/recipes/test_glm53_mtp_state_cuda.py),
[BF16 projection tests](https://github.com/flashinfer-ai/flashinfer/blob/main/tests/experimental/b12x/gemm/test_bf16_gemv.py)
and [component-specific acceptance guidance](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/core-design.md).
The norm-test web fetch was unavailable; its exact pinned local source was read
and hashed instead. The provenance file records both component-bound sources.
The [model card](https://huggingface.co/nvidia/GLM-5.3-Flash-FP4-Local)
describes a vLLM-validated checkpoint; that is not vendor qualification of Flare.

Local review covered Flare/FlashInfer feedback and projection contracts,
vLLM's `glm5next/common/mtp.py` and `fused_eh_norm.py`, exllamav3's GLM/Qwen MTP,
and TensorFold's Nemotron MTP and kernel-reference approach. vLLM's fused norm
uses different rounding; transplanting it would change arithmetic. Use FP64
matched-operand references here, preserving Flare's explicit BF16 rounding
before the norm-weight multiplication. A complete draft-layer and full-model
comparison is stronger and remains separate work.

## Preregistered gate

Window `mtp-feedback-window-20261116T230000Z` may start only after independent
ABBA-window restoration. Freeze checkpoint76348ddb, Flare5a4e867,
FlashInfer4fd836dc, native qualification extensionf394b964 and both runtime
ledgers/wrappers/accepted-core hashes. No serving change in this window.

Run capacities1,4,16,4096 in separate processes on each rank. These represent
decode1/4, speculative4x4 and prefill4096 descriptors. Load the actual BF16
embedding and layer45 feedback weights through the production loader; require
zero Torch copy fallback and byte equality with raw safetensors before and after
execution. Embedding lookup/masking must match exactly. Each RMSNorm output
must stay within the original two-BF16-ULP bound. Projection uses the original
BF16 GEMV `rtol=.01, atol=.01` against a FP64 dot on the same observed normalized
input, rounded to BF16. Do not turn an accumulated end-to-end error into a new
or relaxed component bound.

Each capacity runs normal, small, large, partially occupied and entirely inactive
inputs, five native replays each. Position offsets0/1/255 exercise both masked
and real embedding lookup even at capacity1. Poison outputs before replay; require finite results,
matching native completion fences, unchanged inputs and no allocated/freed
allocation or segment counters across replay. Retain every case's maximum
error and norm ULPs. Both four-case pytest receipts and real unit exit0 are
required; missing/skipped cases fail. No CUDA process overlaps serving.

Use the existing90GiB-free/100GiB-available idle gate between processes, a
continuous notifying1.5GiB-free/8GiB-available memory guard and a90-minute
independent B12X restore timer. Restore the original two B12X images after the
gate, independently verify API/watchdog/tailnet/native-process absence and fresh
5/5 smoke, then disarm the fallback. Snapshot files and runtime hashes remain
unchanged. This gate does not claim draft MLA/MoE, accepted-prefix transactions,
exported-core equivalence or full-model numerical acceptance.

Before execution: pinned prefix AST, bound-source hashes, Python syntax and shell
syntax checked; both-node source manifests verified.

Fixtures and controllers are now staged under the candidate qualification tree
on both nodes; all source-manifest hashes match. GPU execution remains pending.

The frozen window started09:40 UTC after independent ABBA recovery closed.
Controller invocation75085d796a44460b8139bace248ed81d;90-minute fallback armed.
No numerical result is claimed yet.

## Result

The gate passed09:43:23 UTC. Both ranks passed4/4 cases with actual pytest and
wrapper exit0,100 native replay observations per rank and unchanged runtime
hashes. Maximum projection absolute difference was0.015625 under the original
combined rtol.01/atol.01 bound; both norm checks stayed within the original2ULPs.
All35 memory samples were healthy. Receipts: `mtp-feedback-*`.
Independent original-image B12X recovery is underway; full draft/absorption and
broader model/state qualification remain separate gates.

Independent B12X recovery closed09:49:50 UTC: both original images, API200,
watchdog/tailnet, no native processes and fresh5/5 smoke. Restore
e237cafa6bbf40dbadc72ca190c58ce4 and smoke cf94cac97edf4911a73c92d51d3d2ade
ended with actual exit0/PID0; fallback then disarmed.
