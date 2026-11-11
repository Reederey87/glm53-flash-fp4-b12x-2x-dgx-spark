# Startup-only allocator bound — research, not an approved gate

Current state: both ranks stopped after the diagnostic and canonical recovery
failed their2GiB safety floor. Do not rerun either terminal window. Candidate3
is still open. A separate stabilization experiment is necessary before another
backend candidate; no implementation or deployment is approved by this note.

Evidence: `receipts/startup-memory/outcome.md`. At CSF layer6, both ranks reported
92,050,627,584 bytes allocated and117,293,711,360 reserved before the existing
helper reduced reserved to92,197,093,376. Worker host available briefly1.915GiB;
canonical recovery later hit1.561GiB on head. Existing per-module release is
present and functional; adding a duplicate outer cleanup is insufficiently
justified. Changing its20% trigger alone would not eliminate the observed layer6
transient: immediately before that method, the cached gap was only136,315,904
bytes (below the helper's512MiB minimum).

Exa research, followed by local vLLM/EXL3/TensorFold/FlashInfer/Flare review:

- [PyTorch fraction API](https://docs.pytorch.org/docs/2.15/generated/torch.cuda.memory.set_per_process_memory_fraction.html)
  bounds the caching allocator by visible device capacity. This is not a host
  memory reservation or a limit on allocations outside that allocator.
- [PyTorch issue201023](https://github.com/pytorch/pytorch/issues/201023) explains
  why `garbage_collection_threshold` alone can be ignored at the default memory
  fraction. Do not deploy a bare GC flag as a presumed fix.
- Read exact installed PyTorch source from a **never-started** temporary
  container, removed afterward:2.13.0+cu130, git
  `cf30153c4c131c8164ee7798e5022d810682e2cb`. Both fraction getter/setter and
  allocator-backend APIs exist in that pinned image.
- Exa fetched the matching
  [CUDACachingAllocator source](https://github.com/pytorch/pytorch/blob/cf30153c4c131c8164ee7798e5022d810682e2cb/c10/cuda/CUDACachingAllocator.cpp).
  Its explicit allowed-memory check rejects a new native allocation before
  `cudaMalloc` when reserved capacity plus request exceeds the fraction limit.
  The normal retry path releases cached blocks and retries outside graph
  capture; if insufficient, it raises allocator OOM. This supports a bounded
  experiment, not a prediction of success or a global physical-memory ceiling.
- [vLLM proposal49760](https://github.com/vllm-project/vllm/pull/49760) applies a
  related bound to profiling; it is open and its small-model result does not
  prove this post-load case. Our measured phase is CSF postprocessing.

Local/installed sources: loader outer loop; installed Nvfp4CsfMoEMethod and
nvfp4_csf_utils; local FlashInfer experimental/b12x CSF staging and preparation;
EXL3 memory release; Flare transient preparation pools; TensorFold two-layer
in-flight event bounding and phase budgets. Actual installed source differs
from current local vLLM; use hash-pinned installed bytes for any patch. CSF
packing/layout/kernel changes require the compiled-build path and are deferred.

Candidate design for review: apply a native-allocator fraction of0.80 only
around the existing loader postprocess function, including target and MTP
loads, and restore the prior fraction on exit before KV/profile/serving. Require
an already initialized integrated CUDA worker, native allocator and expected
prior fraction; log/read back actual entry/exit fractions and capacity. Preserve
all tensors, quantization, packing and17G KV. Keep common passive phase/hash
receipts so the old failed observation is an explicit unsafe control receipt.
The0.80 choice is provisional until a pre-registered gate and code review: the
recorded live peak was93.008GB, below the approximate102.7GB limit, while cache
reservation reached117.294GB. Allocations outside PyTorch still require the
independent host observer.

Next work: write a distinct gate and implement/test the scoped bound; define
safe stop-only fallback because an automatic canonical restart already failed
its safety gate. Do not silently replay that unsafe rollback or auto-adopt a
passing arm. Require final independent review, exact staged hashes, actual
bound activation/restoration on both ranks, unchanged KV, full smoke/parity and
complete cold-prefill/decode evidence if healthy. Existing full control matrix
is historical evidence; it is not a fresh paired stabilization speed result.
Report that limitation and obtain the required adoption decision only after
concrete receipts exist.
