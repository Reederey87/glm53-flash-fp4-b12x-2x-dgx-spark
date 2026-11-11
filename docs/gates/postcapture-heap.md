# Return measured free heap at the post-capture boundary

Pre-registered dependency for TODO3. One new treatment relative to retained
startup-pinned Humming A: one malloc_trim(0) after the V2 capture_model returns,
before the worker's second warmup. Capture already unfreezes and collects GC.
No added collection, CUDA synchronization/cache clear, host-pinned clear,
workspace resize, program eviction, context-limit change or warmup omission.
Profile-only captures pass through untouched. Preserve the signed capture
memory metric, all graph owners and the existing workspace lock.

Common experimental controls (not production adoption): pinned image3b5da79c,
checkpoint76348ddb, TP2/RoCEnante, targetb12x/B12X, draftHumming MTP3/B12X,
4seats,1Mcontext,4096batch,17GFP8KV/block256/pool2,350,210, default allocator,
prefix/chunking/Max reasoning and existing driver580.173.02/kernel6.17.0-1031.
Same passive trace,0.80 postload bound restored1.0 and pre-KV host-pinned return
with its existing256MiB/128MiB gates and4GiB boundary. That prior full startup
failed; it is not rebooted for a new control number. No paired speed-gain claim.

Exa first: malloc_trim/malloc_info/open_memstream API contracts plus vLLM capture
GC and warmup ownership, followed by all five local trees. Stronger alternative
CUDA stack reclamation is already installed and conditionally used after
benchmarking; do not duplicate it. See docs/research/postcapture-budget.md.

Before restart: freeze exact bytes in a commit; final independent review;
CPU/source AST/syntax and isolated lifecycle checks; real pinned-image native
probes on both nodes/device spellings. Probe uses the actual V2 capture method,
its GC context and real workspace lock, with prepared B12X and pinned-copy
graphs. A bounded512MiB cyclic CPU fixture tests freed-page reclamation only;
its success is not evidence of real-model benefit. Verify current source/image
hashes/env snapshots, a fresh output and>=90GiBfree/>=100GiBavailable both nodes.
Python-only host API patch, no kernel/build/packing contract change.

Actual both-rank gate immediately after real capture completion: one ordered
before/after pair tied to the postload trace PID and exact runner/helper/GC/
workspace/plan hashes. Native integrated CUDA, fraction1.0, outside capture,
completed graph manager and locked workspace; nonzero retained-program owners.
All-arena malloc_info must show>=256MiB free chunks BEFORE trimming. This is
logical free space, not proof of resident/reclaimable pages. Then trim_result1,
RssAnon fall>=256MiB AND MemAvailable rise>=128MiB. Same CUDA allocated/reserved,
pinned active/owned, retained owner identity, lock, GC mode/frozen count,17G KV
and original signed capture result. Otherwise refuse the second warmup.

The independent2GiB floor remains unchanged throughout. Both post-capture
samples must satisfy it; this late boundary already has KV allocated and is
not the pre-KV4GiB gate. No trim is attempted below the2GiB floor. Success here
does not waive subsequent full-startup memory safety, health200, exact KV pool,
actual Humming activation, smoke5/5 with Max reasoning, parity or speed matrix.
Only healthy runs warm once, then20cold-prefill cells8k..128k/c1,2,4,8 with3reps
and3x200-token decode/c plus per-run acceptance deltas; repeat noisy cells.

Fresh local/ab-postcapture-heap through b12x-recipe-window@postcapture-heap.
Every outcome is stop-only: append canonical ledger restoration, verify both
objects absent and proxy/watchdog inactive. No automatic adoption, unsafe A
boot, floor reduction, KV shrink or TODO3 completion claim. Preserve all output.
