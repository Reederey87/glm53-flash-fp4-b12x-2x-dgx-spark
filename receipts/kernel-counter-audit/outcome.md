# PCP inventory explains the model-free return interval

One reviewed fresh default-backend process per node completed with clean exit,
one final marker and the frozen parent/helper bytes. All graph/live-counter/
pointer checks passed. The independent original physical validator rejected
both, as expected. No checkpoint or serving qualification.

| Interval change | Head MiB | Worker MiB |
|---|---:|---:|
| Process Pss_Shmem | -512 | -512 |
| PCP count inventory | +522.766 | +522.113 |
| Buddy free inventory | +0.063 | 0 |
| Reported MemFree | 0 | 0 |
| Reported MemAvailable | -0.438 | 0 |

Counter bundles took0.77–1.28ms. Ordinary reads are not atomic; background
allocations explain why deltas need not balance exactly. No refresh, draining,
wait, sysctl write, fixture enlargement or threshold change. This supports PCP
retention for these intervals, not all causes of the full model's headroom.

The installed kernel is exactly linux-nvidia-6.17=6.17.0-1031.31, source commit
791430b07122e9f9f71644082b2bf18583f3b467. Its PCP-to-buddy accounting and TRYLOCK
path match the observations. Source/config identities and per-file timings are
retained beside raw logs. Never add PCP bytes to the production memory gate.

Next investigate a temporary source-derived PCP cap, with both-node rollback
and a new reviewed gate. No OS-setting or model trial has been cleared here.
