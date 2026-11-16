# Layer replay with the deployed expert precision

> Historical architecture or qualification record. Current production, unresolved gates and the research pause: [docs/63](63-production-pause-checkpoint.md). Old window controllers must be adapted before reuse.

The failed docs/39 fixture called `GlmWeightLoader` without expert_activation.
Its default is A4, independently of the session's native_dense_activations flag.
The pinned serving preparation resolves expert_activation=auto to A16 on SM121
and sets B12X_W4A16_A4_PREFILL=1 before loading. The public recipe.py also explicitly sets A16 for non-SM103 plans; this is not merely an assumed loader default. Thus the failed A4 layer3 output
comparison is retained, but it does not directly qualify the deployed A16
expert owner. The missing deployed-mode layer gate remains a production blocker.

Exa's [CLI contract](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/cli-design.md)
explicitly separates native dense activation choice from routed MoE precision.
The [W4A16 family update](https://github.com/flashinfer-ai/flashinfer/pull/4255)
provides background on packed routing and reductions; current pinned local
bootstrap.py, weights.py and FlashInfer ActivationSpec are authoritative for
this version. Indexed TP-layout prose still says A4; it cannot override actual
pinned preparation. Native export provenance retains SM121, the preparation
source and absence of an expert-activation override. No serving change is made.

Set the qualification loader explicitly to expert_activation=a16 and the same
calibrated-prefill environment before loading, as bootstrap does. Assert actual
expert plan mode=a16, retained calibration scales and experts_a4_prefill on each
routed layer. Preserve all nine cases and every original numerical, state,
routing, allocation and rank assertion. Dense projection mode remains native;
all other docs/39 host adaptations remain. The complete-method AST check records
only these loader substitutions and additional identity assertions. Do not
reinterpret an A16 pass as an A4 pass. The unrun A4 repeatability diagnostic in
docs/41 remains available, but is deferred while qualifying the actual recipe.

Register `layer-a16-window-20261116T120000Z` only after the fixed-output retry
closes with independent B12X restoration and fallback disarmed. Snapshot both
runtime ledgers, accepted core, supervisor and original images; keep exact
private extension f394b964. Both ranks must pass9/9 cases, zero skips/errors/
failures, actual exits0 and all memory observations. Original output tolerance
remains exact for dense and rtol0.01/atol0.001 for routed layers; all intermediate
and state equality checks remain exact. No pass is assumed before execution.

Helpers under `qualification/windows/layer-a16-20261116` retain docs/39's90-minute
fallback,4500-second controller,3900-second rank limits,3600-second pytest,
TCP29677 and memory guards. GPU locks prevent overlapping operations. Restore
B12X on pass or failure; verify both original images, fresh5/5 smoke, API,
watchdog/tailnet and absent test/native processes before disarming fallback.
Representative layers still do not replace full-model, MTP/vocabulary, long
context, capacity or performance qualification.
