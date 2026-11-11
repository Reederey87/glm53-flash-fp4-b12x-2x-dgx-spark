# Later startup pressure after the postload bound

Evidence: `receipts/startup-bound-retry/outcome.md`. The actual0.80 cap passed
both target+MTP scopes/rank, restored1.0, and retained10.132/11.092GiB postload
headroom. At01:58:37Z after graph capture and engine initialization, head fell
to2,063,804KiB available,32.566MiB below the2GiB floor. Observer stopped the
model; no health/smoke/speed. Both ranks are now stopped with proxy/healers off.
Do not repeat that terminal window or claim complete stabilization.

Exa research found primary
[eugr startup cleanup documentation](https://github.com/eugr/spark-vllm-docker/blob/main/README.md)
and its [build patch list](https://github.com/eugr/spark-vllm-docker/blob/main/Dockerfile).
Direct filesystem reads from a never-started pinned-image container confirmed:

- `utils/gc_utils.py:freeze_gc_heap` already collects/freezes and calls glibc
  malloc_trim. GPU workers invoke it after graph/sampler/inductor warmup;
  engine core also invokes it after scheduler/request-hasher initialization.
- `gpu_worker.py` contains host trim before automatic KV sizing, but later
  exact-branch review proved the explicit17G path returns before that trim.
  It does clear CUDA cache and repeats profiling/tuning cleanup before the
  explicit pool; the log reports0.42GiB CUDA cache cleared. Source presence
  alone did not prove CPU trim executed. See explicit-kv-host-heap.md.
- The guard fired around the later engine-core initialization handoff. Workers
  had already logged JIT monitoring and graph capture completion. Do not add a
  duplicate generic malloc_trim/pre-KV cleanup and presume it fixes the issue.

Local source review also covered EXL3's host trim, TensorFold's bounded
preparation lifetime, FlashInfer's compiler pool/preparation session and Flare's
transient-pool synchronization/cache return. Those techniques suggest measuring
lifetime boundaries, not changing quantization or reducing17G KV.

A CPU-only measurement with a disposable no-CUDA container quantified part of
observer overhead (container removed): Docker log follower RSS27,224KiB,
anonymous PSS8,788KiB; the actual completed-line trace safety parser peaked at
18,596KiB RSS and9,244KiB anonymous PSS. This overhead can contribute to a narrow
budget, but these data do not prove it caused the33,348KiB deficit. Neither a
fresh model boot nor a driver/kernel change was made for that measurement.

Next investigation/treatment options, not implemented or approved:

1. Measure allocated/reserved/host memory at the *outer* post-warmup return,
   where temporary locals are out of scope. The installed worker method has no
   explicit final CUDA-cache return after its post-warmup GC. A separate
   measured `empty_cache` hook at that boundary may return unused cached GPU
   memory while preserving live graph/weight/KV storage. Record before/after
   and prove graph replay compatibility; do not infer reclaimable bytes from
   the earlier CSF trace. Hold the qualified postload cap/common observer fixed.
2. Quiesce diagnostic log followers and safety-parser subprocesses after both
   complete postload scopes have been verified, before the tight KV/graph phase;
   retain the independent2GiB observer and recover final logs afterward. This
   changes observer lifetime and should be isolated from any new engine hook.
3. A longer allocator bound through profiling/capture is a stronger but more
   invasive alternative; private graph pools and live KV must fit, so avoid
   choosing a fraction without the relevant phase measurements.

Select one treatment per window, Exa/source proof first, a fresh pre-registered
output, final Astra review before deployment, unchanged checkpoint/quant/17G KV,
healthy-only full smoke/matrix and stop-only fallback. No adoption/candidate3
execution is authorized by this research note.
