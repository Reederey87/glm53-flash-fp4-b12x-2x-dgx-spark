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

Completed compiler-ownership diagnostic now disproves the size premise for a
simple PyTorch metadata clear: tracked payloads10.613/10.365MB,244Triton kernels,
2FX graphs and2bundles perrank; no targeted AOT wrappers observed. No bounded
scan/depth truncation, but native/untracked ownership remains outside scope.
Anonymous mappingRSS3.260/3.255GB and heap1.918/1.915GB remain. Both records
collected before KV with>19GiB host available; stop-only cleanup03:56:34Z.

Further Exa primary [NVIDIA JIT caching documentation](https://docs.nvidia.com/cutlass/latest/media/docs/pythonDSL/cute_dsl_general/dsl_jit_caching.html)
binds executor lifetime to host function pointers, MLIR engine and CUDA modules.
[CuTe disk-cache work](https://github.com/flashinfer-ai/flashinfer/pull/3874)
distinguishes exported object cache from in-process owners. It does not justify
clearing all live compile caches. [B12X warmup fix](https://github.com/vllm-project/vllm/pull/47599)
also explains why dropping shape/workspace specializations can cause mid-serve
compilation stalls. This must remain covered by the full long-prefill/decode
matrix for any eventual lifetime treatment.

Exact native owner source was extracted from a never-started pinned image:
ignored local/native-cute-source/{nvidia,flashinfer,b12x}/, source.sha256;
head /tmp/b12x-native-cute-source/. A disposable CPU-only shell located paths
without CUDA/model initialization, then was removed. Both NVIDIA wheel and
FlashInfer vendored CuTe source exist; runtime import-provider identity must
be proven before patching either.

Pinned JitCompiledFunction stores ir_module, engine, capi_func, artifacts,
export_provider and cached executors. JitModule stores engine and CUDA modules;
its unload destroys kernel libraries. B12X compiler retains a bounded compile
cache and a cached default executor, and exposes clear_compile_cache. These
are ownership leads, not cleanup permission. In particular do not unload modules
or drop an engine that backs live host pointers. Local CSF preparation helpers
are largely Triton, so they cannot simply be assumed to explain native CuTe RSS.

Next inspect/prove active CuTe provider and count the actual native/compiler
owners, export/IR holders and preparation-only versus serving references. The
current diagnostic intentionally did not cover these classes. Only measured,
source-isolated retirement with real pointer/replay proofs could justify a
new candidate. No native cleanup or further model restart was made here.
