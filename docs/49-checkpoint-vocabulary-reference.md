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

## Initial descriptor failure and frozen retry

The initial direct case failed before native execution: `unsupported graph
capacities: head16`. The inherited component signature described16 independent
decode requests while the executor owns four slots. Weight-byte/scale checks,
tuning and capture completed, but no native numerical result was produced.
Both failed test exits remain retained; B12X restoration started automatically.

Exa rechecked the upstream [execution descriptor](https://github.com/NVIDIA/flare-local-inference/blob/main/ignition/preparation/execution.py)
and [core contract](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/core-design.md).
The pinned Rust manifest validator requires batch capacity within owned slots.
Speculative signatures separately describe batch and verification width. Local
Flare validation, vLLM scheduled/speculative token accounting, exllamav3 batch/chunk
limits and TensorFold served-shape contracts confirm the distinction. Raising the
executor slot count would misrepresent the deployed four-slot envelope.

The retry `vocabulary-verified-window-20261116T210000Z` changes only the16-row
descriptor to speculative batch4/width4. One/four-row ordinary decode descriptors
remain. It is still a component-only graph: this does not assert that speculation
or token commit is executed by the vocabulary test. Same kernels, raw FP64 oracle,
row shapes, repetitions, bounds and every original assertion. The declared
substitution is covered by full decorated-method AST equality. Require independent
initial-window recovery before starting; retain all initial failed receipts.

Initial-window recovery closed08:19:06 UTC with both original images and fresh5/5;
fallback disarmed. The corrected retry passed both cases and both wrappers on
both ranks. Each rank observed12 comparisons across direct/indexed modes and
repeats; maximum absolute logit difference0.00390625 remains within the original
relative/absolute bound. Every output finite; byte preservation, exact local
gather, native completion, unused padding and allocation assertions pass.
Independent recovery for the passing window is still pending.
