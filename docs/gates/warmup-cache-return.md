# Return unused CUDA cache after warmup

**Outcome: rejected.** The actual hook returned2MiB/rank, below the64MiB head
gate, without changing live allocation. Later head available fell1.734GiB at
2026-11-11T02:28:58Z; guard stopped before health/smoke/speed. Stop-only cleanup
verified02:29:03Z. Both model objects absent, proxy/healers off. No adoption or
TODO3 verdict. Preserve this terminal output.
[Receipts](../../receipts/warmup-cache-return/outcome.md).

Pre-registered before deployment; final Astra review and both-node real graph
compatibility probes are required first. This is a stabilization dependency of
TODO3, not its completion. No automatic adoption or unsafe rollback boot.

Control evidence: `receipts/startup-bound-retry/`. Native0.80 target/MTP postload
scopes and restoration1.0 passed with10.132/11.092GiB available minima. Later,
after graph/engine warmup, head hit1.968GiB,32.566MiB below the2GiB floor.
That unsafe control will not be deliberately restarted for a fresh speed pair.
Retained historical complete control speed receipts provide context only.

One treatment: call PyTorch `empty_cache()` once, immediately after the original
`Worker.compile_or_warm_up_model` frame returns. Its temporary locals are then
out of scope. Keep live weights/KV/graph objects, original result, seed, graph
capture sizes, synchronization policy and kernels unchanged. No new explicit
synchronization, GC, host-cache clearing, heap trim or ongoing inference hook.
Reject active capture, non-native/non-integrated CUDA or unrestored fraction.
Hash-pin actual installed gpu_worker.py, not current upstream source.

Hold the postload0.80 cap and common diagnostic/observer lifetime fixed. The
recipe adds only this third pre-serve mod. Frozen controls: image3b5da79c,
checkpoint76348ddb, target b12x/B12X, Humming MTP3,TP2,4 seats,1M context,
batch4096,17G FP8 KV/pool2,350,210, unchanged driver/kernel and allocator env.

Exa first: [PyTorch cache contract](https://docs.pytorch.org/docs/stable/generated/torch.cuda.memory.empty_cache.md)
and [graph-pool lifetime](https://docs.pytorch.org/docs/main/user_guide/torch_compiler/torch.compiler_cudagraph_trees.html).
The [pinned allocator source](https://github.com/pytorch/pytorch/blob/cf30153c4c131c8164ee7798e5022d810682e2cb/c10/cuda/CUDACachingAllocator.cpp)
releases unoccupied cache while retained graph pools preserve their references.
Exa also covered host-cache lifetime and stronger alternatives: disabling graphs,
changing KV or carrying a cap through capture would change more controls and are
deferred. Local vLLM sampler warmup intentionally caches max-batch buffers; freeing
those can increase first-use allocation overhead or later fragmentation. The
functional and full speed/memory gates must catch that tradeoff.

Local vLLM, EXL3, TensorFold, FlashInfer and Flare reviewed after lookup. Actual
pinned worker already has CPU heap trims and pre-KV CUDA cleanup; do not add
duplicates. TensorFold/Flare's end-of-preparation cache return motivates this
outer lifetime boundary; it does not move the cluster onto another engine.

Gates before measurement:

-31 CPU tests,34 isolated Linux lifecycle outcomes; exact pinned-source patch
  compilation and AST preservation. Actual pinned frontend emits identical
  serving commands with ordered mods. Final independent review before staging.
- Both-node tiny pinned CUDA probes: indexed/unindexed device, live graph input/
  output pointers preserved,3 correct replays after cache return per device
  spelling. No checkpoint/server; disposable containers removed, assertions on.
- Both actual rank/image/profile/hash proofs and complete postload cap traces.
  One complete new before/after receipt/rank, original fraction1.0, unchanged
  live allocated bytes and non-increasing reserved bytes. Head must return at
  least64MiB (greater than the retained32.566MiB deficit); record worker bytes.
- All postload trace snapshots >=4GiB; every observed warmup/host sample >=2GiB.
  Retain independent2GiB observer. A completed new trace dip fails even if the
  external observer misses it. Source hashes and same worker PID required.
- /health200, exact KV pool, both resolved Humming paths, smoke5/5 incl. Max
  reasoning, parity, once-warmed20cold-prefill cells8k..128k at c1/2/4/8 plus
  three200-token post-ladder decode reps at each concurrency, per-run acceptance
  deltas and engine identity. No health means no performance measurement.

Record initial allocation cost and later memory behavior; repeat noisy/flagged
points before any speed conclusion. This single safety trial is not a fresh
paired throughput comparison. No claim of a model optimization from one answer.

Use single-use `local/ab-warmup-cache-return`, through the existing supervised
template unit only. Every exit—including pass—uses the existing tested stop-only
recovery: canonical ledger restored, both model objects absent, proxy/healers
inactive. Do not replay the unsafe canonical boot, shrink17G KV or silently
adopt this combination. Report receipts and request adoption only after the
concrete result exists; subsequent candidates need their own final review.
