# Complete draft and absorption replay

> Historical architecture or qualification record. Current production, unresolved gates and the research pause: [docs/63](63-production-pause-checkpoint.md). Old window controllers must be adapted before reuse.

Docs/51 covers independent feedback arithmetic. This follow-up executes the
unchanged complete `PreparedMTP` draft and cache-absorption paths using actual
layer45, shared embedding and checkpoint vocabulary weights on both Spark ranks.
Python and Rust replay share the prepared operators and initial state. It tests
composition and native execution; it is not an independent whole-model oracle.

Exa MCP reviewed [MTP design](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/mtp-design.md),
[core acceptance](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/core-design.md)
and the [exported-indexer defect](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/glm-batched-speculation-defect.md).
The design explicitly separates exact metadata/state transfers from arithmetic
with variable reduction order. Indexed search also returns renamed/stale repository
paths; the local pinned5a4e867 implementation is the contract for this experiment.
The stronger exported-core/full-target differential remains separate. Increasing
speculative acceptance cannot substitute for numerical qualification.

After Exa, local review covered Flare's actual MTP, loader, speculative absorption,
MLA/indexer and same-selection tests; FlashInfer norm/MoE component tests;
vLLM's GLM MTP and fused feedback norm; exllamav3's post-target-norm feedback;
and TensorFold's MTP cache ownership and float64 component-reference contract.
No alternative model, precision, normalization order or server is adopted.

## Frozen gate

Window `mtp-replay-window-20261117T000000Z` starts after independently verified
docs/51 restoration. Keep checkpoint76348ddb, Flare5a4e867, FlashInfer4fd836dc,
native qualification extensionf394b964 and all runtime files/settings unchanged.
Each rank runs five separate processes: ordinary draft decode1/4, post-verification
absorption16 (four requests/four rows), and prompt absorption65 live rows in128
capacity and4096 live rows. Draft experts retain ordinary NVFP4/E4M3 scales/A16;
the shared MXFP8 vocabulary head remains at checkpoint precision. No target CSF
A4-prefill policy is applied to draft experts.

Use four disjoint64-page tables in a256-page MLA state, six state slots and the
production twelve-entry C4 tail ring. Three teacher-forced positions/chunks each
run one and four repetitions from matched initial state. Native output readbacks
are poisoned before replay. Observe joined inputs, feedback projection, reduced
attention, MoE input/reduced output and full vocabulary logits. All observed
stages and final outputs must be exact against Python replay on matched sparse
selections; state and metadata remain exact, unused tail slot0 stays zero, and
output agrees across both ranks. Keep the pinned MLA selected-set/cutoff-tie and
physical-index assertions from docs/46; retain uncorrected and matched differences.
No broad whole-model tolerance is invented. Any failure remains a failure and
requires diagnosis, not a widened bound.

Require native completion fences, no allocation/segment counter changes during
replay, five real pytest successes and actual wrapper exit0 on both nodes.
An idle90GiB-free/100GiB-available gate isolates each process. The continuous
notifying memory guard keeps1.5GiB-free/8GiB-available floors, and an independent
90-minute restore timer remains armed until original-image B12X recovery and
fresh5/5 smoke are independently verified. No serving or boot ownership changes.

Status: prepared locally; Python and shell syntax checked; not run on GPUs.

Fixtures and controllers are now staged under the candidate qualification tree
on both nodes; all source-manifest hashes match. GPU execution remains pending.

The frozen five-case/rank window started09:49 UTC after successful feedback
qualification and independent recovery. Controller d8f15995279b4228ba44e1de6e096b24,
90-minute fallback armed. No GPU result is claimed yet.

The first window failed at Gloo initialization before numerical comparison.
Both hostnames resolve to loopback; the fixture omitted Flare's interface binding.
Docs/56 preserves the failure and registers the unchanged-math retry.
