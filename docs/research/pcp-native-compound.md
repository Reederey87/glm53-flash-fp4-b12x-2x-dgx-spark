# Compound lifetime and deadline research

Exa lookup before critical changes reviewed the primary
[CuTe JIT lifetime](https://docs.nvidia.com/cutlass/latest/media/docs/pythonDSL/cute_dsl_general/dsl_jit_caching.html),
[CUDA graph lifetimes](https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/cuda-graphs.html)
and [PyTorch graph integration](https://docs.nvidia.com/dl-cuda-graph/latest/torch-cuda-graph/torch-integration.html).
Compiled executors retain engines/modules; graphed host and device buffers must
stay valid. Stronger than a successful collection: preserve original addresses,
forbid compiler/loader calls and replay both graphs with changed inputs, then
require normal teardown before the final wrapper marker. No cleanup/eviction
is added to the existing observer.

After Exa, inspected vLLM explicit-KV profiling, FlashInfer preparation owner
release after graph teardown, EXL3 pinned-arena synchronization, Flare stored
owner inventory and TensorFold's separate live-reserve accounting. Retain these
lifetime/reserve principles already used by the kit; no engine switch or
fragment sponge. Keep quantization and17GiBFP8 unchanged.

For independent rollback, primary
[systemd D-Bus docs](https://www.freedesktop.org/software/systemd/man/latest/org.freedesktop.systemd1.html)
and timer implementation distinguish actual next monotonic expiry from unit
activation time. The host's systemctl formats NextElapseUSecMonotonic as a
duration string; busctl exposes raw uint64 microseconds. Read that property,
verify the registered duration against actual activation, and check both
nodes' remaining budget before every probe. Do not assume a caller-supplied
600s duration when the actual timer could still be300s.

Exa also checked official [Docker create](https://docs.docker.com/reference/cli/docker/container/create/)
and [start](https://docs.docker.com/reference/cli/docker/container/start/) semantics
before fixing the delayed-launch race. Create exposes a stopped object without
executing its command. Hold the lease lock through creation, then start by its
immutable ID; rollback can remove an admitted object before policy restoration.
A CPU-only real create--rm/start--attach exit17 check propagated17 and removed
the object. Deterministic source-level launch/rollback testing pauses start,
closes the lease/removes the stopped object/restores policy, then confirms that
the resumed start cannot launch GPU work. No broad privileged container is used.
