# Use the serving capture pipeline for MTP replay

> Historical architecture or qualification record. Current production, unresolved gates and the research pause: [docs/63](63-production-pause-checkpoint.md). Old window controllers must be adapted before reuse.

The interface-bound retry reached compilation on both ranks, then failed before
native replay. Legacy `compile_forward` uses FX FakeTensor tracing, which enters
the raw Triton `rms_norm_add_residual` and attempts to read a fake data pointer.
Both first cases failed after about77seconds; preserve these failed receipts.
No numerical comparison completed and no model arithmetic failure is asserted.

Exa reviewed the official [PyTorch Triton compilation guidance](https://docs.pytorch.org/tutorials/recipes/torch_compile_user_defined_triton_kernel_tutorial.html)
and Flare's primary [capture pipeline](https://github.com/NVIDIA/flare-local-inference/blob/main/ignition/preparation/capture.py)
and [AOT implementation](https://github.com/NVIDIA/flare-local-inference/blob/main/ignition/preparation/aot.py).
Local pinned bootstrap calls `capture_forwards`/`ForwardCache` for production
compiled graphs. Its Dynamo path handles Triton launch tracing; the older FX
helper used by this new fixture is a different preparation boundary. Reuse the
production path rather than changing the kernel, suppressing compile errors or
silently falling back to eager serving. vLLM custom-op normalization boundaries,
exllamav3 collective warmup ownership and TensorFold captured MTP rounds were
also checked; none justifies changing the pinned residual norm arithmetic.

## Frozen retry

`mtp-replay-aot-window-20261117T040000Z` requires independent recovery/fresh5/5
and fallback closure of the failed interface-bound window. Keep its interface
correction, checkpoint weights, graph capacities, metadata, state initialization,
all observations and exact stage/state assertions. The entire test body from
random input generation through final cleanup remains byte-identical.

Replace only the legacy compile/manual capture sequence with pinned
`capture_forwards(..., compile_decoder=True, retain_forwards=True)`, the same
RoCE owner/coordinator and an explicit CUDA graph pool. Require both returned
graph and compiled-forward maps to contain exactly`mtp`; native replay still
uses `PreparedExecution`, completion fences and allocation counters. Retaining
the Python forward permits the unchanged matched-state reference. No new custom
operator, normalization order, tolerance or serving artifact is introduced.

Repeat all five cases per rank in fresh processes, with the unchanged memory
floors/idle gates,70-minute controller,65-minute ranks,80-minute notifying guard
and90-minute fallback. Preserve actual exits, XML and source hashes. A compile
failure remains an incomplete gate. Independently restore original B12X images,
API/watchdog/tailnet and fresh5/5 before closing fallback. Capacity still requires
both a successful MTP gate and the unresolved ABBA performance gate.

Local syntax and unchanged numerical-body checks pass. GPU retry is unrun.

The failed compilation window independently restored B12X/fresh5/5 at10:04:42 UTC.
Both failed test wrappers are stopped; restore56f481148da64e1ba655c193f284946f and
smoke042191196cb447dd859c021dd6a7a4c6 ended with actual exit0/PID0. Fallback closed.
The frozen AOT retry started10:04 UTC, controller6cb980dd2d6d4b8aa6ece086d6bb4b23,
with both-node source hashes checked and90-minute fallback armed. Results pending.

Outcome: both first cases failed before replay because the fixture forward was
a local closure rejected by the compiler-worker serializer. Failed evidence is
retained; independent B12X recovery/fresh5/5 closed10:12:07 UTC. Docs/58 corrects
the fixture ownership boundary with CPU-only serialization preflight.
