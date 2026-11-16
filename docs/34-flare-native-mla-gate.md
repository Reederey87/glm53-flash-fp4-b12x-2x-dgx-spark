# TP2 native-activation MLA replay gate

> Historical architecture or qualification record. Current production, unresolved gates and the research pause: [docs/63](63-production-pause-checkpoint.md). Old window controllers must be adapted before reuse.

This is a component gate on the unchanged core's precision path, not a new
serving arm or full-model numerical equivalence. Run only after the docs/33
diagnostic closes with independently verified B12X restoration. Preserve both
runtime ledgers, accepted core, images and supervisor hashes.

Exa reviewed the [native activation contract](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/cli-design.md),
[GLM batched replay defect](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/glm-batched-speculation-defect.md)
and [checkpoint layout](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/tp-checkpoint-layout.md).
Then reviewed pinned Flare MLA projections, replay/state/selector assertions,
FlashInfer sparse MLA reference tests, vLLM sparse MLA grouping, exllamav3
recurrent-state storage and TensorFold's cache/state handling. Whole-model
reference and concurrent prefix tests remain stronger, separate evidence.

Use Flare5a4e867, installed FlashInfer4fd836dc, checkpoint76348ddb and the
existing private qualification extension. No installation, build or core export.
The wrapper verifies the complete upstream test source SHA before import and
sets only `native_dense_activations=True`, matching the accepted core. It fixes
the random seed for repeatability, loads rank1/world2 weights and executes the
original six cases: decode1/2 rows with overlap on/off, and prefill65/4096.

Require all six cases, zero skips/errors/failures and pytest exit0. Original
exact persistent-state/stage comparisons, selector tie-only allowance, finite
outputs, masked rows, graph concurrency and allocation stability remain intact.
Three stateful replays per case cover page boundaries and inactive rows. This
does not test two-host collectives, all45 target layers or mathematical ground truth.

Before stopping B12X: snapshot identities, verify no active requests, arm a
60-minute restoration timer. Stop B12X through its unit, wait for both nodes'
90GiB free/100GiB available idle gate; hold the head GPU-operation lock while
worker stays idle. Enforce existing serving memory bounds during tests. Limit
pytest to40minutes and orchestration to50minutes. On completion or failure,
restore B12X and independently verify original images, fresh5/5 smoke, API,
watchdog/tailnet and absent native PIDs before disarming fallback. Retain XML,
actual exit, source/environment hashes and memory samples. No adoption follows
from this component result alone.
