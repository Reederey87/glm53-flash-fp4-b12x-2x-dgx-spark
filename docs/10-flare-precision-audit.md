# Pinned GLM precision review

This is a source/header audit, not a numerical pass. Checkpoint revision
`76348ddb2be2e35e39ecfc00e75dc07703f4f3d5`, Flare `5a4e867`, FlashInfer
`4fd836d`. The header inventory is in `receipts/flare-checkpoint-metadata-20261115.json`.

The [NVIDIA model card](https://huggingface.co/nvidia/GLM-5.3-Flash-FP4-Local)
describes a mixed-precision QAD checkpoint with losslessly compressed expert
scales. Its validated engine is vLLM; that statement does not qualify Flare.
The indexed file inventory and source loader decide exact projection formats.
This trial does not re-quantize to EXL3 or substitute another checkpoint.

| Area | Pinned source behavior | Remaining evidence |
| --- | --- | --- |
| Target experts | `GlmWeightLoader.load_experts` keeps packed NVFP4/CSF data and calibration, partitions intermediate width over TP2, and retains every expert on each rank. Scale staging validates and repacks compressed components; shared scratch expands scales for consuming kernels. | Exact scale/packed-weight equality and replay correctness on this SM121 build. |
| Activations | `glm53/recipe.py` explicitly selects A16 on SM121. CSF MLP weights retain `experts_a4_prefill`; prefill enables A4 launches. This resembles incumbent `VLLM_B12X_MOE_FP4_FORCE_A16=1` plus `B12X_W4A16_A4_PREFILL=1`, but does not imply equal arithmetic or kernel selection. | Native catalog and accuracy/performance checks. |
| Dense/shared projections | `load_linear_group` requires compatible stored formats, and `load_mixed_linear_group` separates incompatible ones. Layer norms retain stored precision; mHC parameters convert to FP32 for execution. | Per-projection bindings and full-model numerical qualification. |
| MLA absorption | Eleven target `kv_b_proj` matrices are BF16 in `native-QB.safetensors`; `mla.py` uses `BatchedUnquantizedProjection` for tensor weights and a separate packed/scaled path for MXFP8. MTP absorption has FP8 storage. | Match actual exported bindings to headers; compare resulting attention numerics. |
| MTP/vocabulary | Layer 45 is loaded separately through its declared formats. The vocabulary head has FP8 storage, so the conditional auto-NVFP4 draft-head conversion for a plain tensor head does not apply to this checkpoint. No draft-head override is requested. | Export metadata, native speculation/state regression and acceptance deltas. |
| Vision | `--language-model-only` omits vision loading. | Vision requires a separate qualification window. |

Important source discrepancy: the indexed
[TP layout document](https://github.com/NVIDIA/hyperflare-inference/blob/main/docs/tp-checkpoint-layout.md)
says GLM defaults to A4; the pinned recipe explicitly chooses A16 on SM121 and
A4 for prefill. Use the pin and measured bindings when describing this trial.

Source references in the pinned Flare tree: `ignition/recipes/glm53/recipe.py`,
`weights.py`, `moe.py`, `mla.py`; `ignition/components/weights.py`. Reviewed local
vLLM B12X activation controls, exllamav3 quantization distinctions and TensorFold's
observed-cache/exact-token benchmark method. No change to storage precision is
proposed by this audit. Keep the KDA reference, sparse-selection and full-model
atomic-reduction gaps open until supported by hardware receipts.

During tuning, CUTLASS emitted `TYPE_INT_LITERAL_OUT_OF_RANGE` for the indexer's
`Uint32(0xFFFFFFFF) << (32 - ex_round * 8)` masks. Exa located
[CUTLASS #3893](https://github.com/NVIDIA/cutlass/pull/3893), which explains the
narrow-integer constant-fold warning despite wrapped dynamic arithmetic. The
pinned loop skips the shift at round zero and forms 32-bit prefix masks in the
other rounds. This is consistent with intentional truncation, not proof that
indexer replay is correct. Keep the warning in receipts; do not suppress it or
change the kernel/dependency pin inside this treatment. The SM121 indexer gate
remains required.

The next qualification unit includes 12 checkpoint tests from the upstream pin:
`test_glm53_nvidia_weights.py` (four mixed-projection cases), plus the six CSF
partition/scratch and two MTP expert cases selected from `test_glm53_weights.py`.
They compare packed values and scale bytes directly against the pinned snapshot.
The MTP wrapper is adapted only to forward the pinned loader's allocation and
scale-scratch keyword arguments; the original byte-equality checks remain intact.
The target CSF tests use the default A4 owner; they do not establish the actual
SM121 A16 owner's packing or either activation path's arithmetic. The NVIDIA
tests cover BF16 MLA absorption storage, mixed KDA/MLA projections, dense/shared
weights, vocabulary and draft attention. All 12 checks passed on SM121 in the first numerical window. This covers
selected checkpoint partitions, not full-model numerical equivalence.

Exa's [model-preparation documentation](https://github.com/NVIDIA/hyperflare-inference/blob/main/docs/model-preparation.md)
and pinned loader code distinguish storage precision from activation execution.
Local vLLM's ModelOpt loader similarly selects compressed-scale retention by
backend and A16 support. TensorFold's NVFP4 loader explicitly distinguishes
checkpoint arithmetic from W4A16 execution; exllamav3's quantization layout is
different. None substitutes for exact checkpoint tests and native numerical
qualification on this candidate.

## Native-activation evidence and remaining A16 boundary

The native-activation component window now passes all49 registered cases:
12 checkpoint checks, four native indexer replays, two KDA prefix/continuation
cases and31 state-transfer cases. Both KDA relative errors are0.0 under the
original bounds. Full-model core `df214696` subsequently passed startup and
all seven API checks. These results retire the corresponding component/API
gaps; they do not establish full-model numerical equivalence.

Read-only inspection of that signed core reports59 execution graphs per rank,
but `rebuild` and both ranks' `rebuild_weights` are null. Its public graph
catalog lists shape, kind and node counts, not per-projection arithmetic.
Therefore catalog inspection alone cannot prove all selected precision modes.
The resolved export-plan receipt establishes the native-activation option;
the component receipt establishes the measured KDA bindings and behavior.

The A16 scale representation needs a distinct check. At the pinned FlashInfer
revision, `moe/fused_moe/_csf_preparation.py` expands source scales and prepares
a value table with `_nvfp4_compute_scale_factor` and
`_process_nvfp4_packed_scales`. The latter lifts scales by a shared power of two
and128, then zeros values below2 before encoding them. Its upstream
`test_nvfp4_packed_scale_boundary_preserves_normals_and_discards_subnormals`
explicitly covers the boundary. The factor is selected from the maximum across
the projection's experts; testing a small expert subset can select a different
factor from the deployed full layer. A byte-equality claim for lossless CSF
storage therefore must not be extended to every A16 execution value without
checking actual scale populations and the complete layer's factor.

This is a source-identified qualification gap, not a demonstrated failure of
this GLM checkpoint. Exa found a closely related
[SGLang Marlin report](https://github.com/sgl-project/sglang/issues/48906)
and [vLLM rescaling change](https://github.com/vllm-project/vllm/pull/34577).
Their hardware/engine cases do not prove the Flare path fails. The local vLLM
Marlin helper has the same discard boundary, but the incumbent uses B12X rather
than that fallback. TensorFold explicitly distinguishes checkpoint arithmetic
from W4A16 execution; exllamav3 uses a different quantization layout.

Before claiming the deployed A16 path preserves this checkpoint, record the
full-layer scale factors and affected counts, compare rank-local packed values
and reconstructed scales against an independent checkpoint decoder, and exercise
actual A16 plus A4-prefill replay with original numerical bounds. Retain the
upstream native ModelOpt decoder's all-finite-scale test as a stronger alternative
to investigate if the packed boundary affects real weights. Do not substitute
a representation, change calibration or relax tolerances during the current
performance window. No precision or kernel change was made by this review.

The subsequent [selected-layer CPU audit](14-flare-scale-audit.md) decoded every
expert in layers 3, 24 and 44 for both TP2 ranks. All 1,358,954,496 scales are
above the packed boundary; each full-layer maximum is 448 and factor is 1.
The subsequent [full-layer audit](19-flare-full-scale-audit.md) completed all42
target layers:19,025,362,944 scales, zero below the boundary, with independently
validated populations and retained exit0. Actual A16/A4-prefill packing/replay
and full-model arithmetic remain separate requirements.
