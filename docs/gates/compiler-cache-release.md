# Retire compiler lookup ownership after profiling

**Outcome: rejected.** Actual140/128 lookup entries cleared to0,196 retained
owners stable, but only1.4805/0.7695MiB returned versus1GiB. Hooks refused KV;
stop-only cleanup04:30:19Z primary1/recovery0 verified models absent/proxyoff.
No serving tests or adoption. [Receipts](../../receipts/compiler-cache-release/outcome.md).

Pre-registered stabilization window, dependency of TODO3; no automatic adoption.
Retained failed control explicit-kv-host-trim returned<2MiB/rank. This candidate
adds ONE clear_compile_cache call before the same existing glibc trim. No added
GC, CUDA/host cache clear, IR/engine mutation, pool/quant change or global knob.

Exa primary [prepared graph eviction test](https://raw.githubusercontent.com/flashinfer-ai/flashinfer/main/tests/experimental/b12x/preparation/test_startup_capture.py)
explicitly exercises compiler-cache clear with retained prepared graph replay.
[NVIDIA lifetime docs](https://docs.nvidia.com/cutlass/latest/media/docs/pythonDSL/cute_dsl_general/dsl_jit_caching.html)
require executor/engine/module ownership; do not delete native IR or unload
modules directly. A bounded-cache knob is a distinct treatment. Local vLLM,
EXL3, TensorFold, Flare and FlashInfer reviewed after lookup. Exact image compiler
3a73fe9d and compile_plan272ddb4f source pins prove the API and ownership model;
active provider query resolved NVIDIA wheel CuTe, Torch CUDA uninitialized.

After original explicit17GiB profiling returns, completed profile cleanup has
already synchronized. Require no active B12X startup coordinator/profile batch
or current retained preparation context, integrated/native CUDA, fraction1.0,
outside capture. This frozen callback occurs before serving KV/graph creation.
Snapshot compiler lookup counters, CUDA/pinned/host/RSS and the digest/count of
captured retained program owners. The digest uses integer IDs internally but
exports no addresses and holds no extra executable refs across eviction.

Call the pinned compiler.clear_compile_cache once, then common malloc_trim(0).
Require nonempty lookup ownership before, memory-cache+spec-memo sizes0 after,
unchanged retained identity/count, CUDA allocated/reserved/pinned/fraction and
original admission result;>=4GiB host available before/after and>=1GiB worker
RssAnon returned per rank before KV can continue. Otherwise raise/stop before
the unsafe allocation. trim_result0 is allowed if eviction itself returned
pages; boolean trim result is not the reclamation metric. Counter resets are
recorded, not confused with improved hit rates.

Controls: image3b5da79c/checkpoint76348ddb, targetb12x/B12X,HummingMTP3,TP2,
4seats,1Mcontext,4096batch,17G FP8 KV/pool2,350,210, nativeallocator, common
passive trace and0.80 target/MTP postload bound restored1.0; identical driver,
kernel, observer/log lifetime and generated serving script. No other diagnostic
or failed cleanup mod. Fresh processes and in-memory compiler lookups per arm;
disk artifacts stay content-addressed/pinned, no prefix/attention-state reuse.

Before checkpoint: CPU contracts, exactsource/AST/compile, isolated Linux
lifecycle including eager rejection before smoke, identical pinned frontend,
both-node real prepared-B12X/CUDA graph probes, final Astra review and frozen
runtime/image/source/env/memory/fresh-output checks. Real probes capture actual
B12X BF16 GEMV, evict lookups with a cache-owned bounded1.25GiB CPU fixture,
pass the full1GiB gate, retain live CPU guards/pinned/storage pointers and three
correct replays with compiler/loader forbidden. They are compatibility probes,
not evidence of real-model reclamation. Assertions enabled, no checkpoint/server.

Require actual profiles/hash activation/resolved kernels, both full trim/eviction
proofs and complete target/MTP bound traces, every host sample>=2GiB, /health200,
exact KV pool, smoke5/5inclMax reasoning, parity, once-warmed20cold-prefill cells
8k..128k/c1,2,4,8 and3x200-token post-ladder decode perconcurrency with per-run
acceptance deltas. No lifetime counters or single-answer improvement claim.
Inspect mixed-shape/JIT behavior and repeat noisy points before judgment.

This single-arm stabilization compares safety to retained failed controls;
healthy speed alone is not fresh paired performance proof. All exits including
success remain stop-only (canonical ledger, both models absent, proxy/watchdog
off). Single-use local/ab-compiler-cache-release via template unit only. No
unsafe canonical restart, lowered floor, smaller17G pool or candidate3 adoption.
