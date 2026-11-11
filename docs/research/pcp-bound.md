# Bounded PCP hypothesis, Exa before implementation

The paired20bc183 observations show512MiB leaving shared process backing and
~522MiB entering PCP inventory, with no buddy gain. This explains these specific
failed micro physical returns; full-model memory safety remains unqualified.

Primary sources retrieved via Exa before changes:

- [Kernel6.17 physical-memory definitions](https://docs.kernel.org/6.17/mm/physical_memory.html)
- [PCP sysctl documentation](https://www.kernel.org/doc/html/latest/admin-guide/sysctl/vm.html#percpu-pagelist-high-fraction)
- [Initial high-fraction implementation](https://github.com/torvalds/linux/commit/74f44822097c665041010994502b5971d6cd9f04)
- [Autotuning design](https://lists.openwall.net/linux-kernel/2023/09/26/235)
- [Exact installed page allocator](https://git.launchpad.net/~canonical-kernel/ubuntu/+source/linux-nvidia/+git/noble/plain/mm/page_alloc.c?id=791430b07122e9f9f71644082b2bf18583f3b467)

The exact deployed implementation takes managed_pages/fraction/localCPUcount,
floored at4*batch, for each CPU's high_min=high_max. A nonzero value disables
adaptive high tuning. Batch is unchanged. Setting bounds does not force an
immediate drain and high/count can temporarily exceed them (TRYLOCK path).
Restoring0 restores adaptive bounds; it does not recreate the prior inventory.

For512,20localCPUs and4096-byte pages, Normal predicts3098pages/CPU,
DMA124pages/CPU (batch floor), total251.719MiB. Verify actual managed values,
NUMA-local CPU topology, bounds and batch on both nodes before interpreting.
This is smaller than default~1GiB observed stock, but is not a free-memory
promise. Reducing PCP capacity can increase zone-lock contention and affect
CPU/network throughput, so a later model candidate still needs full speed and
acceptance comparisons. No driver/kernel/min_free/quant/KV change.

Stronger alternatives considered: forced drain/stat_refresh changes observation
and latency, lower min_free trades the safety reserve, counting PCP as available
changes the gate, and waiting to success hides interval failure. Reject these.
A kernel rebuild to alter TRYLOCK is disproportionate. Use a bounded temporary
cap test first, with the same512MiB fixture and unchanged physical threshold.

Local trees explored after Exa: vLLM alloc_conf and memory profiling preserve
full configuration; EXL3 PinnedArena uses registered anonymous memory; Flare
memory_inventory attributes owners; FlashInfer b12x testing/memory.py reads
buddy orders and proposes a benchmark-only fragment sponge; TensorFold
cuda/memory_gate.py separates reserve from allocations. None provides a server
PCP control. Adopt the separate-reserve accounting principle already used by
the kit; do not use the sponge or switch engines. Keep17GiBFP8 unchanged.
