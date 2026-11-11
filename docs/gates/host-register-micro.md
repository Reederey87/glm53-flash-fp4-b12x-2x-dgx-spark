# Registered-host allocation: microexperiment only

Terminal micro result: tiny capability/lifetime checks passed on both nodes,
but the fixed-count512MiB A/B comparison FAILED physical qualification in both
arms on both nodes. Register mode changes PSS backing as expected, with only
0/7.805MiB immediate available gain; default gives-0.219/-1.852MiB. All six
graph replays and pointer/live/configuration checks pass. No subsequent compound
probe or model startup is cleared. Raw and independently validated helper
receipts: receipts/host-register/predeploy/memory-outcome.json.

New independent variable: process-start PYTORCH_CUDA_ALLOC_CONF sets
pinned_use_cuda_host_register:True. Native device allocator, registration thread
count1 and disabled reserve segment remain default; no explicit reserve0 token
(the pinned parser rejects it). No model or launch recipe is changed by this
micro gate. Original native-owner compound failures stay FAILED.

Fresh Exa reviewed the exact installed Torch gitcf30153c4c131c8164ee7798e5022d810682e2cb
backend/configuration and CUDA13 host-registration contract, including stronger
cache caps/rounding/explicit arenas. Then all five local codebases were checked.
Exact backend default is cudaHostAlloc/cudaFreeHost; treatment uses malloc+
prefault+cudaHostRegister, followed by cudaHostUnregister/free, with pointer-mode
tracking. Existing event retirement and active-block ownership remain. Neither
path guarantees immediate MemAvailable gain. Per-process configuration affects
all subsequent PyTorch pinned allocations, not merely the idle-return hook.

First review and run exactly one tiny fresh-process capability/lifetime probe
per node. Query HostRegisterSupported, PageableMemoryAccessUsesHostPageTables,
CanUseHostPointerForRegisteredMem, UnifiedAddressing and Integrated. Require
supported integrated UVA devices. Verify effective allocator settings before
allocating pinned tensors; requested environment alone is insufficient.
CUDA host-page-table registration can populate rather than page-lock pages:
do not claim OS locking or assume CPU/device pointer equality. Use PyTorch copy
APIs and actual graph replay. No direct unregister on managed pointers.

Tiny fixture:4KiB active graph-copy buffer and64KiB idle block. Original public
empty-host-cache call must retire the idle block with active/device counters
unchanged;3correct graph replays and stable pre-boundary pointers. This tests
capability/lifetime only, explicitly NO physical-return or checkpoint clearance.
Registration failure terminates its disposable process; no fallback/retry.

Only after tiny review/receipts may a separately reviewed matched fresh-process
default-versus-register512MiB study run. Both use the same current fixture,
setup/prompts/helper, fresh process and native device allocator. Keep original
256MiB idle/128MiB immediate physical thresholds, active/CUDA state and graph
checks. No extra trim/GC/wait, fixture enlargement or substituted accounting.
Require activation proof and record anonymous/shared PSS, cache/free/available
before/resident/cached/after. Preserve A failures; no retry to a passing B.

A micro pass does not establish serving safety, capacity or speed. Any later
model window needs its own frozen treatment/gate, final Astra review, both-node
preflights and actual startup/smoke/full matrix. No lower2GiB floor,17G shrink,
quantization change, driver update or automatic adoption is authorized by this.
