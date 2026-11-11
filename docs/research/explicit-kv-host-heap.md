# Host heap and the explicit-KV branch

Research only; no trimming treatment implemented or adopted by this note.

Exa primary references:

- [Linux malloc_trim contract](https://man7.org/linux/man-pages/man3/malloc_trim.3.html):
  returns unused whole pages in glibc arenas, not live allocations. Return1
  means some pages returned, not a byte-count or proof of sufficient headroom.
- [GNU allocator tunables](https://sourceware.org/glibc/manual/latest/html_node/Memory-Allocation-Tunables.html):
  trim_threshold concerns the top releasable chunk; arena_max changes global
  allocation policy and is a separate treatment. Neither is equivalent to a
  measured single trim at a known completed preparation boundary.
- [glibc interior-page proposal](https://sourceware.org/pipermail/libc-alpha/2026-April/176852.html):
  explains retained free interior pages and the tradeoff in aggressive return.
  This is proposal evidence, not proof that this image contains that patch.
- [vLLM worker](https://github.com/vllm-project/vllm/blob/main/vllm/v1/worker/gpu_worker.py):
  explicit KV bytes still run profiling, then return before the automatic sizing
  path. Actual installed image source, rather than main, decides what executes.

Important correction to the broad wording in late-startup.md: the hash-pinned
gpu_worker.py668921c6 has malloc_trim in determine_available_memory at715..722,
but the explicit kv_cache_memory_bytes branch at635..656 returns first. The
deployed17G request therefore bypasses that particular pre-KV host trim. The
worker's post-warmup freeze_gc_heap trim remains later; the previous guarded
run stopped in kernel warmup before reaching it. Source presence did not prove
execution on this request path. Do not remove existing GC/cache cleanup.

Local review after Exa: vLLM GC freeze is an end-of-startup operation; EXL3
util/memory.py exposes malloc_trim separately from CUDA cache return; Flare
preparation/host_memory.py releases unused arenas at preparation boundaries
and budgets compiled-forward CPU footprint; TensorFold returns retired state
buffers. FlashInfer B12X preparation owns spawned compiler pools, with4 default
workers on Spark and explicit close semantics. Pool lifetime and compile-worker
count are stronger distinct alternatives if direct records identify child
process ownership. Do not change those together with heap trimming.

First obtain the reviewed pre-warmup ownership records. Pinned owned/active
counters can exclude a large pinned-cache hypothesis; process RSS/PSS identifies
where host mappings remain, but does not prove those mappings are free glibc
pages. A trim experiment would need before/after RSS/PSS and host availability,
unchanged live CUDA/pinned allocations, tiny graph/tensor compatibility checks,
final review and a fresh supervised single-treatment window. Full functional
and speed qualification is still required before adoption. Keep17G/quant,
source pins,2GiB observer and stop-only fallback unchanged.

The subsequent entry records are now available in receipts/host-ownership-entry/:
inactive pinned~512MiB/rank, worker anonymous RSS~5.1GiB/rank, no multi-GiB
compiler children among the largest processes. Head floor failed at1.623GiB,
so no passed-diagnostic or serving claim. This supports testing measured heap
return before KV; it does not establish that5.1GiB is all unused heap.

Exa also checked mallinfo2: its counters have allocator/arena coverage and
concurrency limitations. They are not added to this first treatment. Measure
the actual process anonymous-RSS reduction plus unchanged CUDA/pinned counters
and host availability; the callable return1 alone is insufficient. Tiny probes
must pass the same1GiB return gate with live CPU guards and CUDA graph replay.
