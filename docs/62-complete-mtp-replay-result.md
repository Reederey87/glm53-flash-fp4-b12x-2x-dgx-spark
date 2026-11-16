# Complete checkpoint MTP replay passed

> Full MTP replay is complete (docs/62). Further research is paused; warmup is staged but unrun. Current production and safe resume instructions: [docs/63](63-production-pause-checkpoint.md).

The docs/58 retry passed all five cases on each Spark at11:04:18 UTC.
Both rank wrappers and all ten fresh pytest processes exited0 with no skipped,
failed or errored cases. Head invocationf2f704faa12e40cca92c072ce45c0eab;
worker68e2f039562940f89c407b7bf1a423fb. The source manifests and unchanged
runtime hashes passed on both nodes. Expanded CPU preflights independently
completed two fullgraph traces and fresh-process metadata roundtrips per node
without CUDA initialization before production stopped.

| Case | Head seconds | Worker seconds |
|---|---:|---:|
| Draft decode1 | 28.777 | 28.699 |
| Draft decode4 | 103.661 | 104.049 |
| Absorption decode16 | 51.979 | 52.225 |
| Absorption prefill128,65 live | 31.568 | 31.636 |
| Absorption prefill4096 | 39.381 | 39.690 |

All53 continuous memory samples passed; minimum free/available GiB were
105.8734/106.3800 on head and105.5396/106.1872 on worker. The small qualification
model contains checkpoint MTP and shared projection weights; this memory result
does not represent full serving capacity.

Original assertions pass: joined input, feedback projection, attention/MoE
stages and full vocabulary output match Python replay on matched sparse
selections, with exact state/metadata transfers, cross-rank outputs, completion
fences, untouched unused slots and no replay allocation/segment changes.
Three teacher-forced positions/chunks and repeated replay exercise the full
draft and absorption composition. The independent feedback/vocabulary and
layer component bounds remain as previously registered; none was widened.

These results close the full MTP composition/replay item. They do not establish
independent whole-model arithmetic, exported serving-core equivalence, semantic
generation, full hybrid-state reuse or performance. Previous initialization,
FX-capture and serialization failures remain retained under their original
receipt prefixes. The successful fix uses importable fixture observers and the
production capture pipeline, without changing serving kernels or model math.

Independent original-image B12X recovery on both nodes, API/watchdog/tailnet and
fresh5/5 smoke passed; fallback closed11:10:46 UTC. Restore invocation
7b2b734156d84d9281353a5303a6aa23 and smoke72316ec6c94843ef8877cbd6b74cf681
both ended with actual exit0/PID0.
Complete both-rank receipts are retained under`mtp-replay-serial-*`.
