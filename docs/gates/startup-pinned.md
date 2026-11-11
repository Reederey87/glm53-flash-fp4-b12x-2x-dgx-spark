# Startup-only return of idle pinned host staging

Pre-registered dependency for TODO3, one new treatment: one public
torch.accelerator.memory.empty_host_cache call after the original explicit17G
profiling/cleanup returns, before KV allocation. No added GC, synchronization,
glibc trim, device-cache clear or compiler/IR/module mutation.

Reference is retained common-bound Humming A (startup-bound-retry), unsafe to
reboot for a number. Same image3b5da79c, checkpoint76348ddb, targetb12x/B12X,
draftHumming/MTP3/B12Xattention, TP2/RoCEnante,4seats,1Mcontext,4096batch,17GFP8
KV/block256/pool2,350,210, default allocator, prefix/chunking, Max reasoning,
driver580.173.02/kernel6.17.0-1031. Common passive trace and0.80 postload cap
restore1.0. No rejected cleanup/diagnostic mods or B-draft treatment mixed in.

Frozen source/byte manifest and final independent review precede restart.
CPU/isolated lifecycle tests, pinned-source AST/frontend proof, both actual
CUDA probes, images/source/env snapshots, freshoutput and>=90GiBfree/>=100GiB
available on both nodes must pass. Python-only patch; no CUDA build.

Immediate before-KV gate on BOTH ranks: exact source/PID/ordered before-after
pair after completed target+MTP trace; original17G admission preserved;
initialized integrated/native CUDA, outside capture, fraction1.0, no active
startup coordinator/profile batch. Same live device allocated/reserved state,
no new host allocations or active-byte increase. Owned host bytes must fall
by>=256MiB AFTER subtracting any completed-event active-byte decrease, and
host MemAvailable must rise>=128MiB. Both samples retain>=4GiB available.
These thresholds target the independently measured512MiB idle staging owner,
not the failed1GiB glibc/compiler hypotheses. Fail closed before KV if unmet.

Then all actual target+MTP cap/trace evidence, requested/resolved Humming,
unchanged image/KV pool, independent>=2GiB memory floor through the ENTIRE
startup/smoke/parity/matrix, health200 and smoke5/5 including Max reasoning.
Only healthy runs warm once then full20cold-prefill cells8k..128k atc1,2,4,8
plus3x200-token decode reps/c with per-run speculative counter deltas. Repeat
noisy cells. No fresh paired throughput claim from a single stabilization arm.
If it makes common A safe, freeze these common controls for a later TODO3 A/B.

Unit b12x-recipe-window@startup-pinned, fresh local/ab-startup-pinned. Every exit
including success is stop-only: restore canonical ledger, both objects absent,
proxy/watchdog inactive. No auto-adoption, unsafe A recovery boot, lower floor,
smaller17G pool or TODO3 completion claim. Preserve every terminal receipt.
