# Return measured inactive pinned staging before KV allocation

Fresh Exa lookup found PyTorch's public `torch.accelerator.memory.empty_host_cache`
in [44326ea / #171270](https://github.com/pytorch/pytorch/commit/44326ea0f9a826189bbc271df60a17898a1a8c4e).
It releases unused host caching-allocator blocks; it is distinct from device
`empty_cache`, glibc trim and compiler cache eviction. The public API is intended
for use before graph capture. Older `_host_emptyCache` is documented in the
[maintainer discussion](https://github.com/pytorch/pytorch/issues/134332), but
this image has the public API and needs no private fallback.

Pinned image Torch2.13.0+cu130 has the public wrapper SHA
`ffe85913caefd73a2e2cd2866972052d926893a409f53784b348cfda9a9fc214` and
CachingHostAllocator.h SHA
`9ddd1e13154fcebbb3de28bd1bb145ad82954fcff9b689c3f0d9241c09fb7e49`.
Read-only extraction and CPU import initialized no CUDA context. The exact
header's empty_cache first processes completed events, then frees default-pool
free lists and freeable graph pools. Active graph pools/live blocks remain.
Event processing can decrease reported active bytes without releasing live
storage; host stats do not themselves flush pending events. Do not require an
unchanged active counter or confuse pending-event retirement with known idle
staging. Subtract that counter decrease from owned-byte return in the gate.

The earlier entry-ownership receipt measured512MiB already inactive per rank.
Actual TODO3 B initialized but later head1.898GiB failed the2GiB floor after
KV/state binding. No conclusion that512MiB will suffice for all later phases;
measure it and keep the independent guard through full serving tests.

After Exa, local sources reviewed:

- vLLM explicit17G determine_available_memory calls profile_run then its
  finally cleanup (GC, synchronize, device-cache return). Return host cache
  only after that original function returns, before the engine allocates KV.
- TensorFold/TensorFold/src/tensorfold/cuda/direct_read.py Reader.close and
  ReadAhead.close synchronize staging copies then return cached pinned memory.
  This is the useful TensorFold technique adapted here with the public API.
- Flare ignition/preparation/tuning.py release_benchmark_cache and completion
  path call the same public host-cache API after dropping temporary owners.
- EXL3 tests/cache/test_cpu_cache.py uses the legacy host-cache API to establish
  its exact pinned budget. No EXL3 server/kernel replacement.
- FlashInfer preparation closes temporary plans; retain selected programs and
  serving tensors. No CUDA source, packing, quantization or engine change.

Stronger alternatives checked: exported CuTe objects still retain execution
engines/host entry points; blindly unloading them invalidates runtime owners.
The compiler lookup trial returned less than2MiB. API/engine process merging is
not established for this V1 async server. Prefer the measured512MiB native
host-cache owner over speculative compiler/IR mutation or global malloc knobs.

Before a full model: actual pinned-image CUDA probes on both nodes must release
idle512MiB while preserving live pinned storage, a graph using pinned input,
prepared B12X graph replay, tensor pointers and device accounting. The fixture
proves API compatibility only; actual-model return and full memory/smoke/speed
gates remain mandatory.
