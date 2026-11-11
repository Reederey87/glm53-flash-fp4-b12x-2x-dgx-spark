# Remaining post-capture startup budget

Actual pinned-return trial completed graph capture at05:10:36Z and failed the
2GiB available-memory floor on head at05:10:37Z. Reclamation had already passed
both ranks with512MiB known-idle pinned storage returned. There was no health,
smoke or speed result. `receipts/startup-pinned/outcome.md` is authoritative.

Fresh Exa primary research found
[MRV2 sampler warmup OOM #48601](https://github.com/vllm-project/vllm/pull/48601),
[seeded native-sampler first use #54425](https://github.com/vllm-project/vllm/issues/54425),
and [capture GC lifetime #54646](https://github.com/vllm-project/vllm/pull/54646).
They establish that warmup/first-use allocation and graph ownership matter;
their models, versions and memory numbers do not establish this deployment's
cause. Do not remove warmup, shrink KV, or unload graph-owned modules on that
basis. The pinned warmup already includes explicit native sampler warmups.

Read-only extraction from image3b5da79c, without starting its container:

| Installed source | SHA256 |
|---|---|
| gpu/warmup.py | f5b02765e06b200b3cff52874ebbb8b17513fff54381f8f435713d18320c1037 |
| gpu/model_runner.py | aeadc5177c80789112c8e4836639b97e6fbb056711a4e6c81748c7ab9ad805d0 |
| gpu/cudagraph_utils.py | d43c261320ab63558b0975d9265e6ffe4871512bf7f4a448cfa81a8e6821f971 |
| utils/gc_utils.py | e31de173771f6f3eaef4f12a5ec1da3a71f3e1b80aed2bbedd223a86228829d1 |
| utils/torch_utils.py | 6dc04c5be3efb1379f80f23edae0d53f741b6d3d80e6d4d05774fbc9f4e82752 |

Independent source audit agrees on this actual order:

1. Explicit17G skips the automatic-KV worker malloc_trim. The separately tested
   pre-KV trim returned less than2MiB; that says nothing about later free pages.
2. capture_model enters freeze_gc_for_cudagraph_capture. Its finally block
   unfreezes and fully collects **before** the graph-finished log. It does not
   trim glibc pages. Do not claim capture collection was deferred until later.
3. The worker invokes scheduler-realistic warmup_kernels a second time after
   capture to exercise graph-backed paths. It then enables JIT monitoring.
4. Only afterward freeze_gc_heap collects generations, freezes the heap and
   calls malloc_trim. Missing late markers are consistent with stopping before
   this final cleanup; they do not identify an exact failing instruction.

The remaining hypotheses are capture-GC-freed pages retained by glibc, additional
second-warmup transients, or live allocations that cannot be reclaimed. Current
receipts cannot distinguish them. Next measure ownership at capture-context
exit and across second warmup, with a bounded native graph microexperiment
before proposing a measured phase-specific heap-return gate. Extra GC would be
a separate treatment because capture already collected. No checkpoint retry
or new cleanup treatment has clearance from this audit.

Local alternatives checked after Exa: Flare release_unused explicitly pairs
collection and heap trim; EXL3 util/memory.py documents heap fragmentation and
uses trim; TensorFold graph code collects before capture and its reader returns
pinned staging; FlashInfer session closure preserves selected prepared programs
while dropping temporary owners. These support phase/lifetime measurements,
not blind whole-cache eviction. Early CPU-thread/arena policies and smaller
capture sets have no measured benefit here and remain separate hypotheses.


Next evaluation: one measured host trim after the existing capture GC, before
second warmup. Fresh Exa [malloc_trim](https://man7.org/linux/man-pages/man3/malloc_trim.3.html),
[malloc_info](https://man7.org/linux/man-pages/man3/malloc_info.3.html) and
[open_memstream](https://man7.org/linux/man-pages/man3/open_memstream.3.html)
lookup establishes the all-arena API and resource contract. Aggregate free
chunks are logical, not resident bytes; require actual anonymous RSS and host
available-memory gains. Do not add another GC already performed by capture.
All five source trees rechecked for lifetime/heap patterns before code changes.

A stronger CUDA-stack alternative was researched through Exa/NVIDIA context
memory discussions and compared with actual image program_cache SHA361952a1,
preparation wrapper SHA0b8717cc and session6d391f53. The image already implements
initial stack-limit recording and conditional post-benchmark reclamation. A
cached job intentionally skips it; past execution is not proved by presence.
No new losing candidate justifies repeating it after capture. CuTe executor
weak-reference improvements concern final release, not deleting live owners.

The model-free probe now exercises the exact capture method, existing GC and
workspace lock with actual prepared B12X/pinned-copy graphs. Its512MiB CPU
cycle fixture establishes API/lifetime correctness, not model reclamation.
The new full-model gate remains source/PID-bound and fail-closed; no checkpoint
or adoption is cleared until final review and all preflights are complete.
