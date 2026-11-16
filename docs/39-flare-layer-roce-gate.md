# Complete-layer replay on two Sparks — registered, unrun

This extends component qualification to representative complete layers on the
actual two-host fabric. It does not claim full42-layer or MTP/vocabulary acceptance.
The original upstream decoder test assumes local CUDA ordinals and PCIe IPC;
counting its hardware skips would provide no evidence for this cluster.

## Research and adaptation

Exa reviewed NVIDIA's [multi-host preparation contract](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/multi-host.md)
and [model preparation](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/model-preparation.md).
Pinned `test_glm53_query_chain_roce_cuda.py` establishes global ranks0/1 with
local GPU0, explicit fabric interface selection and Gloo coordination.
`create_roce_runtime` and `warmup_wait` provide the serving transport and bounded
extended waits during compiled warmup only. Captured serving graphs retain the
normal peer timeout. Read the GLM bootstrap's decode/prefill capacities before
choosing the same one-shot/two-shot transport pattern.

Also reviewed vLLM's local-GPU/global-rank mapping, exllamav3's collective-free
warmup backend and TensorFold's graph-captured NCCL/rank-order sum. These support
explicit rank mapping and bounded preparation; replacing transport or returning
placeholder collective results in the measured replay would not qualify Flare.
No TensorFold engine, kernel or quantization switch is involved.

`qualification/test_glm53_layer_roce_cuda.py` preserves the entire pinned
Flare5a4e867 decoder `_rank` body except seven explicit substitutions recorded
in `glm53_layer_roce_adaptation.json`: import RoCE/warmup helper, map two CUDA
ordinal uses and executor to local0, require distinct hosts/use RoCE, select the
deployed native dense activation mode, and widen only compiled warmup's wait.
The fixture checks original source SHA and full adapted-method AST on every
case. No numerical assertion, source operand, persistent-state comparison,
router comparison or allocation check is removed or weakened.

## Cases and acceptance

Each rank runs9 cases: layer0 KDA/dense, layer3 MLA/MoE and layer4 KDA/MoE,
each at decode capacity2, prefill65 and prefill4096. Both use checkpoint76348ddb,
installed FlashInfer4fd836dc, native dense activations, deterministic upstream
inputs and private qualification extension SHA f394b964. Preserve original
state/intermediate/rank equality checks; dense output is exact, routed-layer
output retains original rtol0.01/atol0.001. Each case compares one and four
replays with the prepared eager forward. These are native-composition checks,
not mathematical ground truth or a throughput measurement.

Require all9 cases on each rank, pytest exit0, zero skips/errors/failures, both
actual service exits0, finite outputs and all memory checks. `pytest -x` ends a
rank at the first failure; the controller stops both immediately when either
fails. Incomplete coverage is failure, not a reduced passing subset.

## Window and recovery

Only after the long-output window closes with independently verified B12X
restoration may setup create `layer-roce-window-20261116T090000Z`. Snapshot both
ledgers/core/supervisor and original image identities. The worker currently lacks
the private extension: stage the exact existing head-built aarch64 extension
only into its qualification directory, verify SHA and dynamic dependencies,
and preserve any subsequently discovered prior file. No build, package install,
serving extension replacement, core export or runtime recipe change.

Arm `b12x-flare-layer-roce-restore-20261116T090000Z.timer` for90minutes before
B12X stop. Orchestrator `b12x-flare-layer-roce-window-20261116T090000Z` must have
RuntimeMaxSec=4500. Rank units `...-rank0-...` and `...-rank1-...` each have3900s;
pytest3600s. Both hold their GPU-operation locks. Before launch, require idle
B12X requests, no containers/native ranks,90GiB free/100GiB available on both
nodes. Enforce1.5GiB free/8GiB available while testing. Rendezvous is the existing
fabric head address on dedicated TCP29677; no firewall/host configuration change.

The fallback stops the exact orchestrator, both test ranks and memory monitor
before the original B12X restoration helper. Retain each rank's terminal state
before stopping it, XML, environment/source hashes and memory samples. On pass
or failure, restore original B12X images and verify fresh5/5 smoke, healthy API,
watchdog/tailnet and no native/test processes before disarming fallback. No
production adoption follows this component gate. Helpers are under
`qualification/windows/layer-roce-20261116/`; they are not staged yet.
