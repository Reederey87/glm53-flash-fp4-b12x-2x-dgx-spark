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

Each capacity runs normal, small, large and partially occupied inputs, five
native replays each. Poison outputs before replay; require finite results,
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

Status: prepared locally; GPU execution pending. Pinned prefix AST, bound-source
hashes, Python syntax and shell syntax checked.
