# One host heap trim after explicit-KV profiling

**Outcome: rejected before KV allocation.** Actual return1.4805MiB head/
0.7578MiB worker failed1GiB gate. Both hooks refused further startup; cleanup
verified03:31:39Z, primary1/recovery0, both models absent/proxywatchdogoff. No
health/smoke/speed/adoption or TODO3 verdict. [Receipts](../../receipts/explicit-kv-host-trim/outcome.md).

Pre-registered stabilization trial, dependency of TODO3. Original control is
unsafe to reboot; compare safety against retained failed controls. Healthy
single-arm speed receipts do not by themselves establish a fresh paired gain.

Evidence: entry observation shows~5.1GiB anonymous worker RSS,~512MiB inactive
pinned cache, and head1.623GiB before warmup. The actual668921c6 worker's
explicit17G branch returns before the automatic-KV malloc_trim. End-of-warmup
trim is too late. RSS alone does not prove free heap; measure actual return.
[Exa and local research](../research/explicit-kv-host-heap.md) covers glibc,
vLLM, EXL3, TensorFold, Flare and FlashInfer before critical code changes.

One treatment: after the original determine_available_memory returns for the
explicit17GiB request, call glibc malloc_trim(0) once before KV allocation.
No added GC, CUDA/host cache clear, sync, allocator tuning or compiler-pool
change. Preserve the exact original positive integer admission result. Require
initialized integrated/native CUDA, fraction1.0, outside graph capture. Emit
before/after CUDA/pinned/live-state and RSS/host counters with installed hashes.

**Mandatory early gate in the hook before KV allocation can continue:** both
samples >=4GiB host available, unchanged allocated/reserved/pinned-owned/active
and fraction, trim_result1, worker RssAnon reduction >=1GiB per rank. Otherwise
raise before allocating the serving pool; controller keeps stop-only cleanup.
The1GiB threshold exceeds the retained~384MiB entry deficit and leaves margin
for later warmup, but complete-startup2GiB floor remains independently required.

Freeze image3b5da79c/checkpoint76348ddb, targetb12x/B12X, HummingMTP3,TP2,
4seats,1Mcontext,4096batch,17G FP8 KV/pool2,350,210, native allocator env,
common trace and0.80 target/MTP postload bound restored1.0; same driver/kernel,
observer/log lifetime. No terminal ownership or rejected device-cache mod.

Before checkpoint loading: CPU contracts, exactsource/AST/compile, full isolated
Linux lifecycle scenarios including rejected trim proof prevents smoke, pinned
frontend identical serving script, both-node realCUDA probes, final Astra
review, frozenruntimehashes/images/source/env and freshoutput. Tiny probes use
a bounded1.25GiB CPU malloc/free fixture with live guards, indexed/unindexed
CUDA, and live graph/tensor pointers/outputs. Real reclamation must meet the
same1GiB gate; no reduced-threshold probe exemption. No checkpoint/server loaded.

Before measurement: actual rank/image/profile/hash/resolvedbackend proof,
complete target/MTP trace+bound scopes, both exact one-shot trim receipts with
same workerPID and early gate, every observedhostsample>=2GiB, /health200,
exact2,350,210-token KV pool, smoke5/5 inclMax reasoning and parity. Then one
warmup,20cold-prefill cells8k/16k/32k/64k/128k atc1/2/4/8 and three200-token
post-ladder decode reps perconcurrency, per-run speculative counter deltas.
Repeat flagged/noisy points before any performance conclusion. No adoption
from one answer, lifetime acceptance counters, or this single-arm speed alone.

Single-use local/ab-explicit-kv-host-trim, supervised template unit only.
All exits including success are stop-only: canonical ledger restored, both
model objects absent, proxy/watchdog off. Report receipts and ask before any
adoption. Never boot unsafe canonical automatically, lower the floor, shrink
KV or combine another treatment to force a pass.
