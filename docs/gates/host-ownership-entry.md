# Terminal ownership observation before warmup

**Outcome: records collected, head safety gate failed.** Head1.623GiB at the
entry record, worker2.624GiB. Both hooks/PIDs/hashes proven, but no captured-pass
marker or serving tests. Stop-only cleanup03:13:15Z. Records show~512MiB/rank
inactive pinned cache and~5.1GiB/rank worker RssAnon. Preserve terminal output.
[Receipts](../../receipts/host-ownership-entry/outcome.md).

Pre-registered fresh diagnostic, not a serving optimization or TODO3 verdict.
The prior outer-return observation never ran: head1.788GiB at02:59:16Z during
kernel warmup caused its guard to stop. Preserve that terminal output.

One changed observation boundary: decorate compile_or_warm_up_model so its
original body is NEVER invoked. At entry read the same pinned allocator,
CUDA, OS and bounded container RSS/PSS counters, emit one <=4096-byte atomic
record marked pre-warmup, then hold120s and raise. The supervisor stops both
ranks after both validated records. The finite fallback and unconditional
terminal-mode exit prevent any serving-test path, including missing evidence.
No tensor reads, cache clear, GC, sync, profile-history collection or heap trim.

Exact pinned worker668921c6 places entry after17G KV allocation and b12x bind
preparation, before set_torch_threads_for_runtime, kernel_warmup, graph capture
and sampler warmup. This avoids deliberately invoking the known-unsafe work.
If earlier allocation itself crosses the floor, stop with incomplete evidence;
do not retry the same task or claim cache ownership from an absent record.

Exa primary lookup: [vLLM worker](https://github.com/vllm-project/vllm/blob/main/vllm/v1/worker/gpu_worker.py),
[explicit KV configuration](https://docs.vllm.ai/en/latest/api/vllm/config/index.html),
and [UMA safety proposal](https://github.com/vllm-project/vllm/pull/49760).
Upstream locations differ from this image; the actual pinned source is the
patch contract. Explicit KV bypasses automatic sizing and still profiles.
Stronger fallback is a terminal pre-KV observation if entry cannot be reached;
automatic KV sizing or smaller pool would change the requested controls.
Reviewed local vLLM, EXL3 memory budgeting, TensorFold retired-buffer ownership,
FlashInfer CSF preparation and Flare fixture lifetime after the Exa lookup.

Frozen image3b5da79c/checkpoint76348ddb, target b12x/B12X, Humming MTP3,TP2,
4seats,1M context,4096batch,17G FP8 KV/pool request2,350,210; native allocator,
common passive trace and target/MTP0.80 postload bound restored1.0. Same driver,
kernel and independent2GiB observer. Rejected device-cache clear absent.

Before loading checkpoint:37CPU checks, full38scenario isolated Linux lifecycle
suite, exactsource/AST/compile and frontend checks, both real tinyCUDA probes
(indexed/unindexed, original warmup never invoked, active pinned counters,
graph pointer/output preserved), final independent Astra review, frozenhashes,
both immutableimages/sourceidentities, envsnapshots and freshoutput.

Require both rankprofiles, samePID/source hashes, complete target/MTP bound
scopes restored1.0, postload minima>=4GiB, every observedhostsample>=2GiB,
one valid pre-warmup record perrank and diagnostic-captured.txt. The observed
KV sizing is diagnostic context, not serving pool/health qualification. Treat
RSS/PSS/CUDA as overlapping views. Report all ownership values and errors.

Unit b12x-recipe-window@host-ownership-entry, single-use local/ab-host-ownership-entry.
Every exit uses tested stop-only recovery: canonical ledger restored, both model
objects absent, proxy/watchdog inactive. No health, smoke, matrix, adoption or
new engine deployment is authorized by this diagnostic result.
