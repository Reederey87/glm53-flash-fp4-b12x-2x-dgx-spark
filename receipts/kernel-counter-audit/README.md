# Preliminary read-only kernel-counter baseline

Collected ordinary meminfo, vmstat and zoneinfo reads on stopped nodes. No
allocator call, polling, write, cache flush or stat_refresh content read. Only
stat_refresh metadata was inspected:0600/root. Each file read is bounded1MiB;
the bundle is not atomic. This initial parser retains selected PCP fields and
does not claim full schema coverage for a future coupled interval measurement.

Both nodes use4KiB base pages, min_free_kbytes1048576, stat_interval1 and
percpu_pagelist_high_fraction0. Summed PCP counts were1004.70MiB head and
1064.11MiB worker; dynamic high values total about1283MiB. These are inventory
counts, not proven GB10 allocation headroom and not an addition to MemAvailable.

Upstream Linux6.17 sources distinguish buddy NR_FREE_PAGES, PCP occupancy and
per-CPU statistical deltas. The exact Ubuntu/NVIDIA source package still needs
matching. Sources:

- [Free-page reporting](https://github.com/torvalds/linux/blob/v6.17/mm/show_mem.c)
- [Page allocator](https://github.com/torvalds/linux/blob/v6.17/mm/page_alloc.c)
- [Statistics/proc readers](https://github.com/torvalds/linux/blob/v6.17/mm/vmstat.c)

There is no before/after allocation interval in this baseline. It cannot prove
the cause of the earlier512MiB process-PSS return with flat node headroom. Next
evidence should pair bounded PCP/buddy/counter bundles around an unchanged
helper interval, with per-file timing, source review and all original failures
retained. No refresh, PCP draining, sysctl tuning or new model startup is cleared.
