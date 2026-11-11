# Rejected: lookup eviction did not reclaim native footprint

The actual compiler API emptied memory-cache140→0 and spec-memo128→0 per rank.
All196 retained program owner identities stayed unchanged, as did CUDA
allocated/reserved, pinned owned/active, fraction1.0 and the original17GiB
admission result. Correct worker/helper/compiler/plan/PID proof retained.

Actual anonymous RSS returned1,552,384bytes head (1.4805MiB) and806,912bytes
worker (0.7695MiB), far below the pre-registered1GiB/rank gate. Both hooks
refused KV allocation; the controller rejected proof eagerly. No floor breach,
health, smoke, speed or adoption. Synthetic cache-owned probe reclamation was
not taken as evidence of real-model benefit.

Stop-only cleanup verified2026-11-11T04:30:19Z, primary1/recovery0: both models
absent, canonical ledger restored, proxy/watchdog off. Preserve terminal output.
This supports neither repeating lookup eviction nor deleting native IR/engines.
The native ownership is retained by prepared programs; current source and
these measurements do not establish that it can be dropped during serving.

Next return to TODO3's actual draft-B12X arm with its own fresh gate/review.
Retained common-bound Humming startup is unsafe; do not reboot it just to obtain
a paired speed number. A draft-B12X safety qualification can establish supported
startup/functionality and collect speed only if healthy; it cannot establish a
fresh paired throughput improvement against an unsafe control. Keep17G/quant,
the common postload bound and stop-only fallback. TODO3 remains open.
