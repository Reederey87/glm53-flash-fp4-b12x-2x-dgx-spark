# Candidate 3 attempt — control startup failed; B untested

The paired window did **not** evaluate the b12x draft backend. Its fresh Humming
control crossed the pre-registered 2 GiB host-available-memory floor before
health, functional smoke or any performance measurement. Keep candidate 3 open.

The head finished target weight loading at 2026-11-11T00:36:25Z. Seven seconds
later the observer sampled **782,524 KiB available (0.746 GiB)** and stopped
production. Requested control profiles on both ranks had already verified the
pinned image/config, Humming, MTP3, four seats, 17G FP8 KV and no allocator
override. No resolved draft-kernel or B performance conclusion is supported.

Automatic recovery completed **2026-11-11T00:42:32Z**: primary status1,
recovery status0, both restored rank profiles verified, smoke5/5, health200,
serving/watchdog/proxy individually active. An additional unchanged-floor
observer covered the latter part of recovery, then was stopped after validation.
The deployed inference configuration remains the original control.

Exa research found the same post-weight-load failure class in NVIDIA discussion
[7](https://huggingface.co/nvidia/GLM-5.3-Flash-FP4-Local/discussions/7), but this
does not prove our mechanism. Importantly, the installed image already includes
the per-quant-module `release_device_memory_under_pressure` call and the
20%-available/512MiB-cache-release policy described in upstream
[PR45179](https://github.com/vllm-project/vllm/pull/45179). It synchronizes and
empties cached blocks only when its integrated-GPU, releasable-gap and pressure
conditions pass. Adding a duplicate cleanup hook without tracing those
conditions would be unsupported.

Next: collect startup phase/allocator receipts around the existing hook and
quantization postprocessing before selecting a separate stabilization treatment.
Keep quantization, checkpoint and 17G KV fixed. Any such change needs its own
pre-registered window and final review before deployment. Preserve this failed
output directory; do not overwrite it or restart this terminal window as a
successful paired comparison.
