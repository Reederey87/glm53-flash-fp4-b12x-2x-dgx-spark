# Scoped postload bound passed; later startup safety gate failed

Both real-CUDA compatibility probes passed4/4 before loading the checkpoint.
The fresh trial verified both image/profile/source controls and actually applied
the native0.80 bound to target and MTP postprocessing, then restored1.0.

Formal offline validation of the full retained logs passed all postload gates:

| Rank | Complete bound scopes | Traced available minimum | Maximum reserved | Restored fraction |
|---|---:|---:|---:|---:|
| Head |2|10.132GiB|97.328GiB|1.0|
| Worker |2|11.092GiB|97.328GiB|1.0|

Each rank retained1817 ordered trace records; all loader/helper hashes matched,
scope timestamps enclosed the corresponding model phases, and reservation
stayed within the actual native cap. This addresses the earlier postprocessing
cache transient in this observed trial; it does not qualify complete serving.

Startup continued with the original fraction, unchanged17G KV pool and graph
configuration. Logs reached kernel warmup, target/draft CUDA graph capture and
`init engine (profile, create kv cache, warmup model) took41.76s`. At
2026-11-11T01:58:37Z the head observer sampled2,063,804KiB available
(1.968GiB), below the unchanged2GiB floor. It stopped the model before health,
functional smoke or speed testing. No performance verdict or adoption exists.

Stop-only cleanup completed01:58:43Z (primary1/recovery0): both model objects
absent, canonical ledger restored, serving stopped/failed, watchdog/proxy
inactive. Preserve this terminal output; no automatic unsafe reboot. Candidate3
remains untested/open.

Next investigation is the later startup budget, including measurement-process
footprint and reclaimable CUDA/host caches after warmup. Exa found upstream
heap-trim patches; direct inspection of this pinned image proves it **already**
trims glibc after startup GC and before KV sizing and clears CUDA cache before
KV allocation. Do not add another generic heap-trim hook blindly. Worker
post-warmup trim runs before engine-core startup GC; the abort was near that
handoff. These logs do not identify the remaining allocation or prove that
diagnostic overhead caused it. Keep quantization, checkpoint and17G KV fixed;
any next treatment needs a separate gate and final predeployment review.
