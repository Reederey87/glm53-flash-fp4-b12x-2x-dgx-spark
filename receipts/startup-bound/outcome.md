# First bound attempt — API setup failure, treatment not activated

Both pinned images, actual Humming/MTP3/four-seat/17G profiles and all three
installed source hashes matched before startup. At the postload wrapper, both
workers raised `ValueError`: PyTorch's fraction API requires a specified device
index, while this loader passes an unindexed `torch.device('cuda')`.

No bound entry or passive postload record was emitted. The fraction was not
changed; no health, functional smoke or speed matrix was reached. This is an
implementation/API failure, not evidence about allocator-cap effectiveness.

Operator stopped the same supervisor after inspecting the exact error. The
pre-registered stop-only cleanup completed2026-11-11T01:48:13Z, primary143/
recovery0: both container objects absent, canonical ledger restored, serving
stopped/failed and proxy/watchdog inactive. No unsafe canonical restart or
adoption occurred. Preserve this terminal output; candidate3 remains untested.

Exa official PyTorch source review and local CUDA-device patterns preceded the
fix: resolve an explicit index (or current CUDA device after initialization)
for all allocator APIs, preserving the original loader argument. CPU contract
tests now include indexed/unindexed return and exception paths with exact API
device assertions. Final review of the fix and a tiny real-CUDA compatibility
check precede any fresh retry under a distinct name/output directory.
