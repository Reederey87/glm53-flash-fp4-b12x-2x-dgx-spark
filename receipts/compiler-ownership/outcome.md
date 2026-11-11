# Collected: known Python compiler payloads are small

Both complete three-record sets validated at2026-11-11T03:56:29Z with matching
worker/helper/metadata hashes and traced PIDs408/306. diagnostic-captured.txt
exists. Stop-only cleanup03:56:34Z, primary1/recovery0, both model objects absent,
canonical ledger restored and proxy/watchdog off. No KV allocation, health,
smoke, speed, adoption or TODO3 verdict.

Head/worker known payload bytes10,613,341/10,365,237 (~10MiB). Each had244
GC-tracked Triton CompiledKernel,2 CompiledFxGraph and2 TritonBundle instances.
No AOT wrapper instances were observed in this tracked scope. Most payload
bytes were CompiledKernel.kernel (~10MB); graph source/debug strings were small.
Scans1,261,438/1,261,370 objects, no traversal/map truncation, depth omissions
or uninspectable targeted owners. Coverage is still bounded known types, not
all Python/native allocations; uncounted ownership is not proven absent.

Mapping RSS head/worker: anonymous3,260,178,432/3,254,902,784bytes; heap
1,917,538,304/1,915,133,952bytes. Mapping counts3096/3081, below16,384limit.
Host available at collection21.190/22.229GB, above4GiB; collection-entry8GiB
and workerRSS<=8GiB guards passed. CUDA/pinned/fraction unchanged during reads.
Both complete target/MTP postload bound scopes passed/restored1.0. Actual
rank profiles and source hashes matched;17G/quant/controls unchanged.

This does not support clearing PyTorch source/serialized fields as a multi-GiB
fix. No cleanup was performed. Next inspect exact native CuTe/CUTLASS compiler
owners and preparation-only caches. NVIDIA docs bind JIT executor lifetime to
MLIR engine/host pointers/CUDA modules, so whole-cache eviction is not a safe
inference fix without owner isolation and real replay proof. Preparation CSF
helpers in the local tree are largely Triton; do not assume they own the native
CuTe footprint. Source-level and runtime ownership evidence remain required.
