# Post-capture observation: unsafe, forensic evidence retained

Both ranks emitted the source/PID-bound observation at 2026-11-11T06:11:34Z,
after real graph capture and its existing GC, before the second warmup.
The head's 1.840 GiB available failed the unchanged 2 GiB floor. Its raw record
is forensic evidence, **not** a diagnostic pass; the worker's 2.758 GiB record
passed validation. No `diagnostic-captured.txt` was produced.

| Capture-boundary measurement | Head | Worker |
|---|---:|---:|
| Free glibc chunks, bytes | 11,043,009 | 9,967,603 |
| glibc arenas | 86 | 84 |
| Anonymous RSS/PSS, bytes | 5,299,027,968 | 5,639,487,488 |
| Anonymous huge pages, bytes | 1,776,287,744 | 2,120,220,672 |
| CUDA allocated, bytes | 109,496,164,352 | 109,496,164,352 |
| CUDA reserved, bytes | 110,155,005,952 | 110,155,005,952 |
| Pinned owned = active, bytes | 150,998,056 | 150,998,056 |
| Retained program-key/owner tuples | 228 | 228 |

The roughly 10 MiB free chunks rule out the proposed >=256 MiB glibc trim
precondition at this boundary. No trim was performed. The floor breach already
exists before second warmup; its transients cannot explain this observation.
The tuple count does not establish distinct engines, binary copies or bytes.
Anonymous RSS and CUDA counters overlap on unified memory and must not be added.

Both actual profiles retained Humming MTP and the original 17 GiB KV controls.
All quant traces, two restored postload-bound scopes and the common 512 MiB
idle-pinned return proofs validate. Capture/workspace completion and fraction
1.0 were observed. Original signed capture metrics (-30,064,640 / 355,999,744)
are retained; a negative delta is not proof of zero capture memory cost.

Stop-only cleanup completed 06:11:41Z, primary=1/recovery=0: both model objects
absent, model/controller MainPID=0, canonical ledger restored by appending,
proxy/watchdog inactive. No second warmup, health, smoke, parity, speed,
adoption or TODO #3 completion. Do not restart this terminal output.

Next investigate distinct native owners and canonical AOT artifact sizes before
any load-path experiment. Preserve strong graph/executor ownership; no blind
cache or engine eviction. Every subsequent deployment requires final review.
