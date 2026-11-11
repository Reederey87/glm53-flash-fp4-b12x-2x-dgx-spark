# Preregistered ordinary PCP/buddy observation

Exact installed source package linux-nvidia-6.17=6.17.0-1031.31 corresponds to
official tag Ubuntu-nvidia-6.17-6.17.0-1031.31, peeled791430b07122e9f9f71644082b2bf18583f3b467.
Selected source files were fetched at that commit. No kernel update/build.
Source distinguishes PCP inventory, buddy NR_FREE_PAGES and statistical deltas.
The TRYLOCK free path can temporarily exceed PCP high; do not reject that data.

After review, run exactly one fresh default-backend process/node. The frozen
83f453512MiB parent test and8e4e residency sampler stay byte-identical. Only add
bounded ordinary counter bundles after its cached-process sample, before the
helper baseline, and after the helper returns/raises. No measurements inside
the helper's original before/after interval. Original result may change under
instrumentation, but cannot retroactively qualify earlier failed tests.

Read meminfo/vmstat/zoneinfo/buddyinfo, record each file's timing and actual
base page size, online CPU/zone/order coverage, PCP count/high/batch/min/max/
threshold, and PGFREE/PGALLOC counters. Reads are not atomic and take locks;
ordinary NUMA-event folding is not free-page refresh. Bound each file, total
CPU rows and bundle time<=1s; malformed/truncated/incomplete data fails closed.
Both installed configs have ARCH_FORCE_MAX_ORDER=13 (14 buddy columns),
PCP_BATCH_SCALE_MAX=5. Require all five deployed PGALLOC fields and all online
CPU rows for present zones, including present-but-unmanaged zones. Timing
includes parsing and aggregation; it is an acceptance bound, not interruption.
Require final B12X_KERNEL_RETURN marker plus clean process exit.

No stat_refresh content read, allocator operation in the counter collector,
polling, added wait, drain, cache flush, sysctl write, fixture enlargement or
threshold change. Keep min_free_kbytes1048576/stat_interval1/PCPfraction0 and
the existing512MiB fixture, helper and graph checks. All model units remain off.

Compare PCP-count bytes and buddy-list bytes with reported-free and PSS deltas.
PCP growth matching PSS loss supports a cache-inventory hypothesis; buddy growth
without counter growth suggests statistics/skew; neither leaves attribution
unresolved. No addition of PCP to MemAvailable or production gate. This is
counter evidence only, with explicit candidate/checkpoint qualification false.
