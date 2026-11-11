# Ownership measured; head safety gate failed

Both reviewed pre-warmup hooks emitted exactly one record. Head available was
1,743,089,664bytes (1.623GiB), below2GiB; worker2,817,335,296bytes. The complete
trace safety check correctly rejected head, so diagnostic-captured.txt is
absent. Stop-only cleanup verified2026-11-11T03:13:15Z, primary1/recovery0,
both model objects absent, canonical ledger restored, proxy/watchdog off.
No health/smoke/speed/adoption or TODO3 verdict.

Exact source/PID/phase records are retained despite the failed floor. Do not
describe this as a passed diagnostic: head-ownership.json explicitly retains
its gate error. Worker ownership validation passes. Both common postload
target/MTP scopes passed, restored1.0;1817 ordered records/rank; postload minima
10.136GiB head/11.307GiB worker. Requested17G KV unchanged.

Each rank owned687,868,505bytes pinned, active150,997,580bytes, inactive
536,870,925bytes (~512MiB). That is not a multi-GiB pinned-cache explanation.
Worker RssAnon5,489,672,192/5,488,295,936bytes (~5.1GiB); VmRSS7.309/7.334GB.
Head also has API process1.526GB anonymous and engine0.649GB. No multi-GiB
compiler child processes appear among the largest processes at this boundary.
RSS/PSS/CUDA overlap on UMA; never sum them as disjoint ownership.

The explicit17G path returns before the installed automatic-KV malloc_trim.
Existing post-warmup trim remains too late for this peak. Free glibc pages are
not proven by RssAnon; measure a single earlier trim's actual reclamation before
allowing KV/startup to continue. See docs/research/explicit-kv-host-heap.md.
