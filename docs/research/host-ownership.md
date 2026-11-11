# Remaining late-startup ownership — diagnostic next

The device-cache-return trial was rejected: only2MiB/rank returned, vs64MiB
pre-registered head threshold. Late head available1.734GiB still crossed2GiB.
Both models are stopped; no health/smoke/speed or adoption. See raw/validated
`receipts/warmup-cache-return/`. Do not repeat that terminal window.

Exa primary research:

- [Pinned allocator lifetime](https://docs.pytorch.org/devlogs/eager/2026-08-09-pinned-memory-allocator/):
  deleting a tensor does not necessarily unpin its pages. Owned bytes include
  active plus cached blocks; active bytes include checked-out/pending work.
  Captured host addresses must remain valid for graph lifetime.
- [Host statistics](https://docs.pytorch.org/docs/stable/generated/torch.cuda.memory.host_memory_stats.md)
  expose allocated_bytes.current, active_bytes.current and num_host_free.
- [Public empty-host-cache contract](https://docs.pytorch.org/docs/stable/generated/torch.accelerator.memory.empty_host_cache.md)
  returns only unoccupied cached host blocks, a separate allocator from CUDA
  device empty_cache. Pinned live graph buffers must not be freed.
- [Exact matching legacy CUDA graph source](https://github.com/pytorch/pytorch/blob/cf30153c4c131c8164ee7798e5022d810682e2cb/torch/cuda/graphs.py)
  already invokes _host_emptyCache before capture. Direct pinned-image source
  confirms accelerator.Graph does likewise, and the public host API exists.

Therefore host cache is a hypothesis, not a demonstrated missing cleanup.
Do not infer its size from total-used minus native CUDA bytes: driver allocations,
active pinned buffers, library workspaces, CPU heaps, kernel pages and parent
processes can contribute. Worker CUDA allocated/reserved at the last boundary
was109.496/110.157GB; only2MiB was actually returned.

Next safe action: a separately reviewed diagnostic at the post-warmup boundary
that records owned/active host counters, CUDA allocated/reserved and mem_get_info,
OS memory fields and worker/engine/API-process RSS without reading data or env.
Prefer an intentional controlled stop at that boundary, before the later unsafe
engine-core allocation. Preserve the proven0.80 postload bound and17G KV; no
performance claim or auto-adoption from a diagnostic. Pre-register a new output,
final review, tiny API probe and stop-only fallback before loading weights.

Use those receipts to select a single treatment. Potential candidates include
unused host-cache return, earlier CPU lifetime cleanup, bounded library workspace
configuration or observer lifetime reduction. Each requires source/ownership
proof and graph compatibility; do not clear library workspaces whose addresses
may be captured, relax the floor, or shrink the requested KV pool as a shortcut.

For the terminal observation, Exa also verified the
[Linux proc ABI](https://docs.kernel.org/filesystems/proc.html) and
[smaps_rollup ABI](https://kernel.org/doc/Documentation/ABI/testing/procfs-smaps_rollup).
PSS apportions shared pages; RSS counts each mapping's resident view. Neither
can be added to CUDA reserved on UMA. VmLck/VmPin do not replace the pinned
allocator's own ownership counters. Read aggregate rollup fields, not all VMAs.
Detailed PyTorch allocation history is a stronger follow-up if aggregates are
insufficient, but adds collection overhead and is not enabled in this first read.

Post-lookup local review: vLLM worker and engine call freeze_gc_heap, while
distributed/parallel_state.py already knows empty_host_cache; EXL3 util/memory.py
distinguishes integrated host availability and native reservation; TensorFold
qwen4_exp/cuda/multi.py returns retired buffers rather than live state; Flare
ignition/preparation/tuning.py retires preparation fixtures before host-cache
release. FlashInfer's experimental/b12x CSF preparation owns actual quantization
buffers. These support measuring ownership at a known boundary, not freeing
live host/graph buffers or copying another engine's policy without evidence.
