# Preserve full-target process isolation

The first docs/43 window was stopped during first-case autotuning at07:43:07 UTC,
before any completed target result. Its two-host fixture called both capacities
inside one pytest process, whereas upstream spawns fresh GPU workers for each
capacity. This omitted a lifecycle property of the original harness. No memory
failure or numerical failure is claimed; the last observed memory was about27GiB
free per host. Preserve the aborted logs and restore B12X before retrying.

Exa MCP reviewed [PyTorch CUDA graph memory](https://docs.pytorch.org/docs/main/user_guide/torch_compiler/torch.compiler_cudagraph_trees.html)
and [graph lifetime](https://docs.pytorch.org/docs/main/generated/torch.cuda.CUDAGraph.html).
Graph pools and live owners can retain allocations; releasing selected tensors
is not proof that all process-local model/compiler state has gone. The pinned
Flare test explicitly uses `mp.spawn` per capacity, and `compile_forward` retains
prepared buffers/forward owners. Local review also covered vLLM spawned workers,
exllamav3 model/shared-tensor unloading and TensorFold explicit resource ownership.
Fresh process exit plus measured memory recovery is preferable here to adding
unproven garbage-collection/reset calls or lowering the idle-memory floor.

## Frozen retry

`target-isolated-window-20261116T190000Z` keeps the exact docs/43 numerical
fixture, source adaptation, library/checkpoint hashes and both capacities.
The rank wrapper launches a separate uv/pytest child for65 and4096, sequentially,
with one exact test node per process. Record distinct launcher PIDs, per-case
XML/actual pytest exit and local pre-case memory observations. Each case requires
90GiB MemFree and100GiB MemAvailable before loading (up to60s); both ranks enforce
this locally. Existing Gloo initialization synchronizes the rank pair. Keep the
outer3600-second combined case deadline and3900-second rank bound,4500-second
controller,90-minute fallback and notify/watchdog memory guard.

Require both cases and both wrappers exit0, zero skipped/errors/failures, complete
memory samples and unchanged runtime hashes. A failed or absent case remains
incomplete. The prior clean9/9 representative-layer gate remains required, as do
independent recovery and fallback disarm for the aborted target window. After
this retry, independently verify B12X recovery/fresh5/5 before closing fallback.
No serving image/core, numerical bound, host driver or kernel changes.

Aborted-window recovery independently closed07:49:53 UTC: both original images,
fresh5/5 smoke, API/watchdog/tailnet and restore/smoke exit0. Fallback disarmed.
The isolated retry then started with both-node source hashes verified; no result
is claimed yet.
