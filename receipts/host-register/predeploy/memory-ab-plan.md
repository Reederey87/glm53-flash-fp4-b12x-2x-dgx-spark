# Preregistered same-size default/register comparison

Tiny c4eb5af tests passed once per node with effective treatment proof, all five
capabilities1,64KiB idle retirement and3host-copy replays. Host-page-table access
is enabled, so OS page-locking is not claimed. This is not physical clearance.

After source review, run exactly one A(default), then one B(register) per node,
each in a fresh standalone process. Only process-start PYTORCH_CUDA_ALLOC_CONF
changes from empty to pinned_use_cuda_host_register:True. Clear generic/HIP
allocator variables, enforce source revision/native backend/default threads1/
no reserve segment and an unoptimized interpreter. Use identical pinned image,
current fixture recipe, prepared B12X/pinned-copy graphs and sampled boundaries.

Both arms retain512MiB idle fixture size and original helper1761e9ae thresholds:
>=256MiB eligible idle return and>=128MiB immediate MemAvailable gain, unchanged
active/device counters.10GiB entry headroom, no extra wait/trim/GC/retry or other
allocator flag. Record actual effective settings before pinned allocation and
PSS_Anon/PSS_Shmem/cache/free/available before/resident/cached/after. Keep helper
exceptions as failed outcomes. No samples inside its original gate interval.

Run3prepared-B12X plus3host-copy graph replays with compiler/loader forbidden
after observation; preserve original pointers and owners. An A physical failure
can still supply safe model-free compatibility evidence, but remains failed.
B is micro-qualified only if helper and graph checks pass on BOTH nodes.
One pair does not establish a robust speed or physical-improvement estimate.

If B qualifies, a separately reviewed fixed batch of compound native-collector
probes on both nodes/device spellings may follow, preserving prior failures.
No checkpoint startup is cleared by this plan. A later model window must retain
17G/quant/floor and go through its own source review, gate, smoke/full matrix.
