# Incomplete: guard stopped before ownership boundary

Terminal 2026-11-11T02:59:21Z, primary1/recovery0. Head MemAvailable fell to
1,874,672KiB (1.788GiB) at02:59:16Z, during kernel warmup before graph capture
and before the outer warmup-return hook. Worker minimum3,358,352KiB. Both
containers absent; model failed/stopped, watchdog/proxy inactive. Canonical
ledger restored without an unsafe recovery boot.

**No ownership records were emitted.** No diagnostic-captured marker, health,
smoke, speed, adoption or TODO3 result. This is an incomplete observation, not
an empty pinned-cache finding. Do not retry this terminal task.

The intended bytes were active in both actual containers: worker54b3f8b1,
helperd137d0bd. Actual rank profiles and immutable images matched. Both complete
target/MTP allocator scopes passed and restored1.0;1817 ordered traces/rank,
postload minima10.308GiB head/11.320GiB worker. Final review,35CPU,38isolated
lifecycle scenarios and both tiny CUDA probes passed before checkpoint loading.

This boot crossed its floor earlier than the preceding device-cache-return
trial, before the diagnostic could execute. Outer-return placement is too late
to guarantee evidence. Fresh Exa primary worker/UMA research supports observing
at compile_or_warm_up_model entry, before JIT/kernel/graph work. Exact pinned
worker source confirms that entry follows KV allocation and b12x preparation.
Use a new gate/output, source review and final independent review; do not relax
the floor, reduce17G KV or infer ownership without direct counters.
