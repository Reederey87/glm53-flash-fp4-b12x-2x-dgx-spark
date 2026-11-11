# Registered-host backing hypothesis

The matched fixture-only study observed512MiB in Pss_Shmem and Cached while
resident, then removal after cudaFreeHost with almost no immediate node free/
available gain. Both old/current fixture recipes behave this way. That does
not establish the cause of driver or Linux accounting behavior.

Fresh Exa primary sources:

- [Exact Torch CUDA host allocator](https://raw.githubusercontent.com/pytorch/pytorch/cf30153c4c131c8164ee7798e5022d810682e2cb/aten/src/ATen/cuda/CachingHostAllocator.cpp)
  pairs default cudaHostAlloc/cudaFreeHost versus malloc/register/unregister/free
  and retains each pointer's allocation mode. Reserve-segment memory is retained.
- [Exact configuration](https://raw.githubusercontent.com/pytorch/pytorch/cf30153c4c131c8164ee7798e5022d810682e2cb/c10/cuda/CUDAAllocatorConfig.h)
  gives CUDA-specific environment precedence and defaults register=false,
  registration threads1, reserve0. The pinned worker reads/restores live settings
  when temporarily changing split size, preserving unrelated fields.
- [CUDA13 registration contract](https://docs.nvidia.com/cuda/archive/13.0.0/cuda-runtime-api/group__CUDART__MEMORY.html)
  requires actual capability checks. Host-page-table registration may populate
  pages without page-locking them; pointer equality is capability-dependent.
- [PyTorch allocator lifetime](https://docs.pytorch.org/devlogs/eager/2026-08-09-pinned-memory-allocator/)
  distinguishes active owners, event retirement and cached ownership. Cache caps
  and rounding controls are alternatives, but neither changes default backing.

All five local trees were examined after Exa. FlashInfer loader/_bounce.c uses
aligned allocation plus registration for checkpoint staging. EXL3 PinnedArena
registers anonymous mappings and unregisters before releasing them. Flare's
HostRegion explicitly distinguishes UMA registration from locking and checks
device aliases. TensorFold carveout/fabric code pairs registration with reverse
lifetime cleanup; its DRM/IOMEMORY behavior is not transplanted. vLLM allocator
configuration preserves full settings during scoped changes. These support a
source-based microexperiment, not a claim of GB10 support or physical benefit.

The chosen first test uses PyTorch's existing backend rather than porting a
custom arena, extending CUDA kernels or directly unregistering managed memory.
It changes neither checkpoint packing/dtype/layout nor the17G pool. More register
threads, reserve segments, explicitmlock and custom mapped arenas are distinct
treatments and remain out of scope. Gate: docs/gates/host-register-micro.md.
