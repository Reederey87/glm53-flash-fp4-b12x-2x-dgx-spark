# Startup observation failed safety; cluster left stopped

The reviewed diagnostic-only control did not reach health, functional smoke or
the speed matrix. Candidate3's b12x draft arm was not attempted. No optimization
was adopted; keep candidate3 open.

Both ranks prove the expected traced-loader/helper hashes. Each retained1817
ordered records covering603 quant-module/release calls, including31 releases
and the target model's postload exit. Both report an integrated GPU. This is
target postprocessing evidence, not a completed target+draft startup.

The lowest snapshots were routed-expert layer6, `Nvfp4CsfMoEMethod`:

| Boundary | Head | Worker |
|---|---:|---:|
| Host available after quant method, before release |2.099GiB|1.915GiB|
| Allocated at that boundary |92,050,627,584 bytes|92,050,627,584 bytes|
| Reserved at that boundary |117,293,711,360 bytes|117,293,711,360 bytes|
| Reserved minus allocated |25,243,083,776 bytes|25,243,083,776 bytes|
| Existing helper returned |true|true|
| Reserved after existing helper |92,197,093,376 bytes|92,197,093,376 bytes|

The worker's below-floor interval was shorter than the external observer's
sampling cycle. On discovering it in the passive trace, the operator wrote an
explicit safety-abort receipt and stopped the window; no benchmark was allowed.
The hook is present and effective after the method returns, but that boundary
can follow a dangerous cached-memory transient. These observations do not
identify every allocation inside CSF conversion or prove a repair.

Canonical untraced recovery was itself guarded. At2026-11-11T01:24:32Z the head
sampled1,637,192KiB available (1.561GiB); its observer stopped the model. Recovery
terminated at01:24:38Z, primary143/recovery1. Both containers are absent;
serving is failed/stopped, watchdog timer/service and proxy are inactive. Host
memory recovered. The terminal failed window must not be restarted, and no
automatic unguarded retry is permitted.

Raw logs are preserved as deterministic gzip artifacts; hash-checked trace
summaries include the exact minimum boundary/context. CSV/abort/unit-status
receipts accompany them.20 CPU tests and24 final isolated Linux lifecycle
scenarios passed before this window, with final independent review clearance
at4d4d66a. The real failure demonstrates the configured stop behavior; it does
not count as smoke or a successful restoration.

Next dependency: evaluate a separate startup-only native-allocator bound that
can trigger cache reclamation or a clean allocation failure before host
exhaustion, then restore the allocator limit before KV/profile/serving. Preserve
checkpoint, quantization and17G KV. This is a proposal, not implemented/tested.
Exa found PyTorch's
[fraction API](https://docs.pytorch.org/docs/stable/generated/torch.cuda.memory.set_per_process_memory_fraction.html),
[allocator GC caveat201023](https://github.com/pytorch/pytorch/issues/201023)
and vLLM's [UMA cap proposal49760](https://github.com/vllm-project/vllm/pull/49760).
The GC environment flag alone can be a no-op without a memory fraction; do not
deploy it on documentation alone. A changed layout/packing or CUDA kernel would
need a compiled build. Any next implementation requires its own gate and final
review before deployment; no further unsafe canonical restart is authorized by
these receipts.
