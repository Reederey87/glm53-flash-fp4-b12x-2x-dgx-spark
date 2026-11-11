# Device-cache return rejected

The treatment activated on both ranks after the original warmup returned.
Source hashes and worker PID matched, live allocated memory stayed identical,
and graph compatibility probes had passed. It returned only2MiB per rank,
below the pre-registered64MiB head threshold. This is not a sufficient repair.

At that boundary both ranks reported109,496,164,352 bytes live and
110,157,103,104 reserved. After cache return, reserved was110,155,005,952 bytes.
The larger reserved-minus-live gap was not entirely releasable device cache;
retained graph pools can own it. Do not equate that gap with reclaimable bytes.

The held postload0.80 cap remained valid: two target/MTP scopes/rank restored1.0;
postload minima10.248/11.466GiB. Existing CUDA graphs and17G KV stayed unchanged.

After engine initialization, the head hit1,817,796KiB available (1.734GiB) at
2026-11-11T02:28:58Z. The unchanged2GiB observer stopped it before health,
functional smoke or speed. Stop-only cleanup finished02:29:03Z,
primary1/recovery0: both model objects absent, canonical ledger restored and
proxy/healers inactive. No adoption or candidate3 evaluation occurred.

31 CPU tests,34 isolated lifecycle outcomes, exact-source/AST checks and both
real-CUDA probes passed before the reviewed trial. Each real probe preserved
live graph pointers and passed6 replays/node. Those checks establish compatibility,
not sufficiency or speed. Raw compressed logs, validated phase records and
CSV/abort receipts accompany this outcome.

Next: determine the remaining host/pinned/parent-process ownership before
another cleanup change. Exa found the public pinned-host allocator statistics
and empty-host-cache contract, both present in pinned PyTorch2.13. However,
the matching CUDA graph context already empties host cache before each capture;
the accelerator graph API does likewise. Do not add another generic host-cache
flush on the assumption that freed pinned pages account for this deficit.
Collect actual owned/active host bytes and worker/engine process RSS at the
post-warmup boundary, then choose a separate reviewed treatment. Preserve17G,
quantization, graph behavior and the safety floor.
