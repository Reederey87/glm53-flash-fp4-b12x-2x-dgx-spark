# Startup-only allocator bound qualification

Pre-registered before restart. This stabilization dependency keeps TODO3 open.
Final Astra review is required before deployment. No automatic adoption.

Unsafe control A: `receipts/startup-memory/`, same image, recipe and common
passive instrumentation. Target CSF layer6 left25.24GB reserved-minus-allocated;
worker host available dipped1.915GiB. Canonical recovery subsequently hit1.561GiB
and stopped. Both ranks are now absent. Do not deliberately replay that unsafe
boot for a fresh speed baseline. This is a safety qualification against retained
control evidence, **not** a fresh paired speed comparison.

Independent treatment: a native caching-allocator fraction0.80 only around the
existing postload function. Validate initialized integrated CUDA/native allocator,
prior fraction1.0, entry reservation below the bound, active fraction0.80; restore
and read back1.0 on normal or exceptional exit. No added empty-cache, GC,
synchronization, tensor conversion, packing/layout, kernel, checkpoint, KV or
serving-policy change. The first mod is the same passive trace as A; the second
hash-guarded mod adds only this decorator. API/source proof and stronger options
are in [research](../research/startup-bound.md); Exa lookup and local
vLLM/EXL3/TensorFold/FlashInfer/Flare review preceded implementation. Adopt the
scoped preparation-budget technique, not an alternate server or weight format.

Frozen: image3b5da79c, checkpoint76348ddb, TP2, target b12x/B12X,
Humming draft MTP3,4 seats, context1M, batch4096,17G FP8 KV/pool2,350,210,
default allocator env, existing driver580.173.02/kernel6.17.0-1031 and caches.
Actual serve command must remain byte-identical to A. No CUDA build is needed.

Gate before any measurement:

- Both actual rank profiles/images and all installation hashes match frozen
  bytes. Complete ordered per-module trace and at least two completed bound
  scopes/rank (target and MTP), same PID, fraction0.80 entered and1.0 restored.
- During postload: every completed trace snapshot >=4GiB host available; native
  reservation <=the logged cap. Independent host observer retains its2GiB
  floor throughout the window. Completed trace lines are also checked during
  boot so a short below-floor interval cannot vanish between external samples.
- Both resolved Humming kernels, exact17G KV capacity, /health200, smoke5/5
  including Max reasoning, and parity receipts. No health means no speed test.
- Warm once;20 cold-prefill cells8k/16k/32k/64k/128k x c1/2/4/8; same200-token
  decode budget,3 strict post-ladder repetitions at each concurrency; per-run
  acceptance counter deltas and engine identity. Validate the full matrix.

Compare with the retained complete historical default-control matrix only as
context; repeat flagged/noisy points before claiming a robust >2% regression.
No fresh-A speed causal claim and no throughput optimization verdict from this
single arm. A passing result qualifies startup reliability for an explicit
adoption decision; it does not complete the draft backend candidate.

Rollback/fallback: **stop-only**, on every exit including a passing gate. Stop
watchdog timer/service, proxy and production through its unit; verify model unit
not running and both container objects absent; stop observers. Append canonical
RECIPE/image/default allocator to the ledger without starting the known unsafe
control. Independent ExecStopPost repeats cleanup after interruption. A success
receipt means verified stopped state, never healthy serving restoration.
Any failed cleanup retains recovery-required and access closed. Output is
single-use `local/ab-startup-bound`; preserve both prior failed directories.

After concrete receipts, report the stopped state and ask before adopting the
stabilization recipe. Do not automatically expose this arm, restart unsafe A,
change quant/KV, or proceed to candidate3 as though stabilization were approved.
