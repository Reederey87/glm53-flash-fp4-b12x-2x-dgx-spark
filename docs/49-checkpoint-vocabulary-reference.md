# Checkpoint vocabulary reference gate

The isolated complete45-layer target replay passed both capacities65/4096 on
both ranks (docs/48). This checks finite target logits and replay invariants;
the remaining vocabulary check compares actual checkpoint arithmetic with an
independent reference. It does not claim complete MTP-body or model equivalence.

Exa MCP reviewed the pinned upstream
[vocabulary test](https://github.com/NVIDIA/flare-local-inference/blob/main/tests/components/test_vocabulary_cuda.py),
[MTP design](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/mtp-design.md),
[NVIDIA MXFP8 representation](https://docs.nvidia.com/deeplearning/transformer-engine/features/low_precision_training/mxfp8/mxfp8.html)
and [CUTLASS block-scaled GEMM](https://docs.nvidia.com/cutlass/latest/media/docs/operators/tutorials/006_block_scaled_gemm.html).
MXFP8 weights have E4M3 values and power-of-two UE8M0 scales per32 K-elements.
The pinned GLM target and MTP share the vocabulary head; its explicit default
is A16 even when native dense activations are enabled elsewhere.

Local review covered Flare's vocabulary/projection/loader and MTP implementations,
FlashInfer's MXFP8 packing and scale-layout inverse, vLLM W8A16 partition handling,
exllamav3's direct exponent-scale reconstruction, and TensorFold's kernel contract.
The useful TensorFold technique here is an independent FP64 dot reference from
original operands. A second quantized GEMM would share more failure modes; no
new server or kernel is introduced. Full MTP and exported-core comparisons remain
separate evidence. Current indexed web revisions may differ from the pinned source.

## Preregistered window

`vocabulary-checkpoint-window-20261116T200000Z` keeps the serving core, checkpoint,
quantization, runtime wrapper and production ownership unchanged. The fixture
adapts the whole decorated upstream `_rank` method with explicit substitutions
and AST verification. Two fresh processes/rank test direct and indexed outputs.

Load only the actual two77440-row head shards. Compare packed value bytes and
reconstructed compact scale bytes exactly against raw safetensors. Build reference
weights directly from those raw checkpoint values times `2**(scale-127)` in FP64;
reject nonfinite values and UE8M0 NaN codes. Compute FP64 local dots, round once
to BF16 and gather over independent CPU/Gloo transport. This oracle never reads
native output or uses the serving GEMM/quantizer to calculate expected logits.

Test1/4/16 rows, indexed expansion to32 slots, and repeated native launches with
the original completion, allocation, exact gathered-shard and untouched-padding
checks. Keep original BF16 bounds `rtol=.016, atol=.002`; additionally require
all logits finite. Require both tests and wrappers exit0 on both ranks, unchanged
runtime hashes and healthy memory observations. Preserve all failures and error
maxima. Do not widen bounds in response to a failure.

Use the tested notify/watchdog memory guard, independent90-minute rollback timer,
fresh-process90GiB free/100GiB available gate, and existing fixed safety floors.
Snapshot both runtime ledgers/hashes before stopping B12X; no concurrent client
work may be active. After the fixture, restore the original B12X images and
independently verify5/5 smoke, API, watchdog and tailnet before fallback disarm.
No result is claimed until those receipts exist.
