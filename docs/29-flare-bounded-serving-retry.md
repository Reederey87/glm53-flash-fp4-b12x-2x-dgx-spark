# Bounded scheduler serving retry — conditional registration

> Historical architecture or qualification record. Current production, unresolved gates and the research pause: [docs/63](63-production-pause-checkpoint.md). Old window controllers must be adapted before reuse.

This repeats docs/26's unchanged performance gates only after docs/28's loaded
lifecycle gate passes and its B12X restoration is independently verified. It
introduces no new scheduler, core, quantization, memory or native binary change.
The corrected supervisor is fixed in both fresh arms. The prior balanced result
is retained, but is not reused as the sole reference for this new comparison.

Window `bounded-retry-window-20261116T050000Z`, with180-minute restoration armed
before stopping B12X and original two-node idle/serving memory bounds. Exact
helpers live in `qualification/windows/bounded-retry-20261116/`; setup refuses
without prior lifecycle-pass and restoration/disarm receipts.

Frozen native artifact127424e9 / binaryb2eb310b, coredf214696,
checkpoint76348ddb, TP2,4slots,MTP3,chunk4096,CP-off,reserve4,T1/.95, traceoff.
Wrapper SHA41b65a5a (full value in the peer-drain source receipt) is fixed.
Independent variable remains balanced versus bounded-latency scheduling.

1. Observe B12X idle, stop watchdog and B12X unit, verify both containers gone.
2. Fresh balanced start: verify actual binary/argv/core on both ranks,7 API
   checks, then all75 mixed requests/9 cases over three repetitions.
3. Verify both actual native exits0/no forced kill before transition. Fresh
   bounded-latency start, identical identity/API checks and75 mixed requests.
4. Compare every registered mixed point using the unchanged strict comparator.
   A separated >2% regression fails; an overlapping bad median requires
   investigation/repetition. Do not advance unresolved points into full speed.
5. Only if mixed passes, run84 full matrix rows against the retained B12X
   reference (315 matching request hashes), with decode and speculative metrics.
   Retain every request's timings. No adoption from aggregate throughput alone.
6. Numerical, state, long-context/capacity, nontrivial long-prompt outputs and
   final production/reboot gates remain. Source boot controls remain disabled.

Any unexpected failure/deadline queues B12X restoration. Fresh5/5 smoke, original
images, API/watchdog/tailnet and inactive native processes are required before
closing this window. Record results and keep unresolved tasks in spec/TODO.md.

Record live KV page/token capacity on both fresh arms. The memory-sized pool
can vary across startups despite the same reserve; do not substitute the original
export observation for current capacity. This is additional measurement, with
no pool-setting or adoption-threshold change. See docs/12.
