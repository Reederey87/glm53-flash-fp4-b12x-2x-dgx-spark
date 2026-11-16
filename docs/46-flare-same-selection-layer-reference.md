# Complete-layer comparisons on matching sparse selections

Docs/45 collected nine observations on each rank. All three paths—eager,
Python graph and native graph—vary on repetition: attention max difference
0.001953125, while attention-normalized inputs and persistent state repeat
exactly. All values remain finite. Both original assertions still fail; all12
memory samples pass. This rules out a native-only replay explanation. It does
not yet establish that the variation is numerically acceptable.

Exa MCP fetched the [upstream MLA checkpoint test](https://github.com/NVIDIA/flare-local-inference/blob/main/tests/recipes/test_glm53_mla_cuda.py)
and reviewed [numerical acceptance](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/mtp-design.md).
The upstream test explicitly recomputes attention using native selector order,
validates selected sets (including equal-score cutoff ties), and checks physical
slot expansion exactly. The complete-layer test lacked this operand alignment.
The pinned MLA test SHA is2d22226f190e272b565f585561d7ee4c5dac88c35ee352dc258eb0ec9083fca0;
the new helper imports that exact validator rather than inventing a looser tie
rule. Local review covered Flare indexer/MLA/decoder, FlashInfer selection and
reduction contracts, vLLM's stable top-k DCP path, exllamav3's tiled pooled top-k
and TensorFold's shape/reference and repeatability requirements. A deterministic
selector is a stronger serving alternative, but would change the exported graph
and require separate numerical and speed qualification; it is not this change.

## Preregistered qualification-only reference correction

Window `layer-matched-window-20261116T170000Z` retains the deployed A16 owner,
calibrated A4 prefill, native dense activations and nine representative cases
per rank. Observation copies expose the actual selector scratch from captured
MLA execution; they do not change selections or arithmetic. After replay, save
the native outputs/state and recompute the eager reference on the native
selection. First require exact query bytes, weights, pool lengths, page tables
and selected lengths; validate selected sets with the pinned cutoff-tie validator;
independently expand selected pools and require exact physical slots. Restore
the identical initial state before the eager sequence, require its final state
to match native exactly, then restore native observations for assertions.

Only the expected output/stages receive this matching-operand reference.
Every original exact stage assertion, original output rtol0.01/atol0.001,
cross-rank equality, allocation and persistent-state assertion remains. Retain
uncorrected and corrected differences plus selection order/set receipts. This
is an explicit reference correction, not a claim that the old fixture passed.
If a matched-operand stage still differs, fail and investigate that operator;
do not widen bounds or infer acceptance from generation quality.

The full upstream-method AST comparison permits the documented host/deployed
mode adaptation plus observer/reference calls. All9 cases per rank and actual
exit0 are required. Memory readiness/watchdog/OnFailure,90-minute fallback,
4500/3900-second controller/rank limits, GPU locks and memory floors remain.
Start only after independently verified docs/45 B12X closure. Confirm restoration,
fresh5/5 smoke, both original images, API/watchdog/tailnet and no test/native
processes before disarming fallback. Full-target replay remains subsequent work.

## First hardware observation

All9 pytest cases pass on both ranks. In both4096-token comparisons (one/four
replays), selected pool sets match exactly while order differs. With the native
order, every intermediate and final layer output is bit-exact on both ranks;
uncorrected final-output maximum differences were0.3701171875/0.39892578125.
No cutoff-tie substitution was needed for these observed sets. This identifies
selection order as the discrepancy in this case. The wrapper-name rejection
and clean rerun are retained separately in docs/47. It does not establish
whole-model quality or eliminate every possible sparse-selection boundary case.
