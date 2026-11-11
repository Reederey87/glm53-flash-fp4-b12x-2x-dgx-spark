# Compiler metadata ownership before KV allocation

Fresh terminal diagnostic, dependency of TODO3; no cleanup, optimization or
serving qualification. Actual malloc_trim returned<2MiB/rank while worker
RssAnon was~5GiB. Inactive pinned ownership was only~512MiB. Do not infer free
heap, a current compiler leak, or a multi-GiB host cache from those measures.

Exa primary [PyTorch compiler ownership](https://github.com/pytorch/pytorch/commit/ac91f8765ba7817a0853f0520e7f9c94768babc2)
and [bundle source](https://github.com/pytorch/pytorch/blob/e9ebbd3b/torch/_inductor/triton_bundler.py)
describe metadata/binaries in cached autotuners. [Python GC](https://docs.python.org/3/library/gc.html)
only exposes tracked objects; [getsizeof](https://docs.python.org/3/library/sys.html#sys.getsizeof)
is shallow. [Linux smaps](https://docs.kernel.org/filesystems/proc.html) adds a
native mapping view. Allocation tracing is a stronger follow-up with added
overhead, not enabled here. Local vLLM/EXL3/TensorFold/FlashInfer/Flare and exact
pinned vLLM/Inductor source reviewed after lookup. Flare's serialized-state
retirement has engine-specific invariants; this diagnostic copies no cleanup.

One observation: after original explicit17G profiling returns, before KV,
aggregate GC-tracked known compiler classes, deduplicate builtin byte/string
payload sizes, and classify self smaps into heap/anonymous/file/stack/special.
Bound scan2million GC objects, metadata walk100,000nodes/depth6 and
smaps16,384VMAs. GC's initial snapshot is a bulk list, so require>=8GiB host
available and current worker VmRSS<=8GiB before collection. Record truncation,
depth omissions and uninspectable types. Counts are lower-bound metadata views,
not a complete allocator inventory. No arbitrary repr, source/payload output,
tensor reads, object mutation, GC collect, cache clear, sync or heap trim.

Emit three <=4096-byte atomic records: objects, maps, then primary memory LAST
as readiness signal. Each shares worker/helper/metadata source hashes, PID and
timestamp. After output hold120s then raise; never return to KV allocation.
The supervisor requires both complete validated sets, profiles, full target/MTP
trace/bound proofs, then stops both ranks. Unconditional terminal-mode exit
also rejects unexpected startup success with missing records. No serving path.

Frozen image3b5da79c/checkpoint76348ddb, targetb12x/B12X, HummingMTP3,TP2,
4seats,1Mcontext,4096batch,17G FP8 KV request, common passive trace and native
0.80 target/MTP postload bound restored1.0. Same drivers/kernel/observer/logs.
No rejected trim/cache-clear or older terminal diagnostic mod. Pool capacity
request remains2,350,210tokens, but this stops before allocation/health.

Before checkpoint: CPU aggregate/privacy/dedup/bounds/terminal/validator checks,
exact source/AST/compile/frontend, full isolated Linux lifecycle including
missing/invalid compiler evidence, final independent Astra review, both-node
real tinyCUDA API probes preserving CPU/pinned/graph objects, staged frozen
hashes/image/source/env/memory preflights and freshoutput. Probes use controlled
compiler metadata fixtures and test that payload contents/paths are absent.

At completed collection require>=4GiB headroom, unchanged live CUDA/pinned/fraction across
metadata reads; all observed samples>=2GiB, complete target/MTP bound scopes and
postload minima>=4GiB. Exactly one complete three-record set/rank with matching
phase/source/PID; record all bounded-coverage limitations explicitly. Both
validated sets plus diagnostic-captured.txt constitute collected evidence,
never a serving pass or total native-memory ownership proof.

Unit b12x-recipe-window@compiler-ownership, single-use local/ab-compiler-ownership.
All outcomes stop-only: canonical ledger restored, both model objects absent,
proxy/watchdog inactive. No health/smoke/matrix/adoption or TODO3 verdict.
Select the next single treatment only from actual ownership/source evidence.
