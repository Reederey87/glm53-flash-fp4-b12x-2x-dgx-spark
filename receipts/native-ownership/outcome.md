# Native-owner collector: implemented, compound qualification failed

No checkpoint was loaded and production remained stopped. Frozen de7fe05
compound probes failed on both nodes before collection:512MiB idle allocator
return, but head-0.219MiB/worker0 immediate available-memory gain. The unchanged
128MiB physical gate rejected both. Their raw failures are retained.

Independent review found missing mandatory carrier keys, disconnected graph
acceptance and a deadline excluding root/finalization work.224fb01 fixes these
with singleton/dialect requirements, typed connected relationships/key unions,
and an end-to-end deadline.24focused native CPU tests plus12 common/profile
checks pass,64isolated Linux lifecycle scenarios pass, and the actual pinned
launcher serving bytes remain22bffdb2. No production controller change.

The preregistered matched fixture-only study ran exactly one old/current pair
per node, in fresh processes, without new waits/GC/trim/size/threshold changes:

| Variant | Head immediate available gain | Worker gain | Physical gate |
|---|---:|---:|---|
| Old fixture recipe under current setup | -0.219MiB | 0MiB | Failed both |
| Current fixture recipe under current setup | -0.219MiB | 0MiB | Failed both |

Both recipes add512MiB Pss_Shmem while live and remove it after the helper;
Cached follows that change, anonymous RSS remains flat and MemFree is unchanged
over the interval. This rejects the fixture rewrite as an established cause.
It does not explain driver backing/OS accounting or qualify physical return.

Separately reviewed schema-only exploration passed on both GPUs. Each observes
one selected CuTe program, executable, engine and materialized CUDA module, with
the owner/cache and shared-engine edges validated. Collection took0.187/0.217ms.
Compiler and loader calls were forbidden during collection and replay;3B12X and
3host-copy graph replays passed with original pointers. It invokes no common
pinned-return treatment and explicitly denies compound/checkpoint clearance.

Both model objects remain absent, model MainPID0 and proxy/watchdog inactive;
see predeploy/terminal-state.txt. No KV allocation, health/smoke/speed/adoption
or TODO3 completion. The next source-supported hypothesis is a distinct
registered-host allocation backend, beginning with tiny capability/lifetime
checks; source support alone establishes no GB10 compatibility or memory gain.
