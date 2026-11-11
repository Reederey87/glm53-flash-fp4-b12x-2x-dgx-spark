# Retained compiler/preparation ownership: next investigation

Actual explicit-KV trim returned only1.4805/0.7578MiB, so an earlier trim is
rejected. Inactive pinned ownership was~512MiB/rank. The multi-GiB anonymous
worker footprint remains unexplained; neither measure proves a generic leak.
Both models are stopped; do not replay terminal windows or relax17G/floors.

Fresh Exa primary sources:

- [vLLM AOT artifact design](https://github.com/vllm-project/vllm/pull/25205)
  describes deduplicated serialized compiled bytes plus reconstructed runnables.
  Serialization and execution ownership differ; that does not prove retained
  bytes on this exact image or authorize dropping execution guards.
- [AOT cache placement](https://github.com/vllm-project/vllm/pull/39718)
  distinguishes on-disk unpacking and memory lifetime. Moving cache directories
  is not evidence of a process-RSS fix.
- [Pinned cache/wake fix](https://github.com/vllm-project/vllm/pull/57629)
  concerns discarded wake backups. This kit is not executing that wake flow;
  its measured inactive pinned bytes are only512MiB.
- [Historical Inductor leak](https://github.com/pytorch/pytorch/issues/96937)
  was fixed years earlier. Do not transplant an old fix or upgrade from it
  without identifying the current retained owner.

After lookup reviewed local vLLM compilation/caching and backends, Flare AOT
capture lifetime, TensorFold state retirement, EXL3 memory budgeting and
FlashInfer preparation/pool ownership. Exact installed sources were extracted
from a never-started immutable3b5da79c image container, then removed. No CUDA,
checkpoint or serving was started. Ignored local copies:
local/retained-compiler-source/{vllm,torch}/; hashes source.sha256. Originals
on head /tmp/b12x-retained-compiler-source/. Treat these as authoritative over
current upstream, which differs from this fork.

Source leads, not implemented fixes:

- Pinned vLLM caching.py308..350 loads mega artifacts and reconstructs
  PiecewiseBackend runnables; finalize_loading skips that mega path. Inspect
  references through StandaloneCompiledArtifacts and runtime wrappers.
- Pinned torch/_inductor/output_code.py CompiledFxGraph retains source_code,
  runnable_graph_str, provenance strings, _triton_bundle, optional serialized
  original graph and execution constants/callables. Their actual byte ownership
  must be measured and deduplicated before any field is changed.
- Flare preparation/aot.py BoundForward.prepare_capture explicitly releases
  its own serialized artifact and serializer owners, source/provenance strings
  and Triton bundle while keeping guards and kernel owners. Its storage-bound
  closed-forward invariants are engine-specific; do not copy wholesale into
  vLLM. retire_after_capture removes guards only after captures in that engine.

Next safe action: a separately reviewed terminal diagnostic after explicit
profiling, before KV allocation. Aggregate known compiler/preparation object
counts and byte/string lengths without printing contents, reading tensors,
mutating fields, disabling guards or collecting allocation history by default.
Deduplicate shared owners and bound the output. Preserve full postload traces,
allocator/host counters, source pins, independent memory guard and stop-only
cleanup. If aggregates are insufficient, evaluate bounded allocation tracing
as its own diagnostic before a cleanup candidate. No fix or adoption is implied.
