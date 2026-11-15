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
weights, vocabulary and draft attention. These GPU tests are prepared, not run.

Exa's [model-preparation documentation](https://github.com/NVIDIA/hyperflare-inference/blob/main/docs/model-preparation.md)
and pinned loader code distinguish storage precision from activation execution.
Local vLLM's ModelOpt loader similarly selects compressed-scale retention by
backend and A16 support. TensorFold's NVFP4 loader explicitly distinguishes
checkpoint arithmetic from W4A16 execution; exllamav3's quantization layout is
different. None substitutes for exact checkpoint tests and native numerical
qualification on this candidate.
