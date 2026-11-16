# First Flare build and deployment attempt

> Historical architecture or qualification record. Current production, unresolved gates and the research pause: [docs/63](63-production-pause-checkpoint.md). Old window controllers must be adapted before reuse.

This prerequisite window is authorized by the user's `go forward` and subsequent
request to try the candidate on the cluster. It cannot establish adoption.

Frozen: NVIDIA checkpoint `76348ddb`, Flare `5a4e8679`, FlashInfer `4fd836dc`,
two SM121 ranks, four slots, fixed MTP-3, 4096-token prefill, text only, context
parallelism disabled. No host driver/kernel or incumbent configuration change.
Both vendored RoCE proxies declare ABI 14. Upstream issue 276 reports a
cross-host context-parallel binding failure; that path is disabled in this arm.

Native Ubuntu dependencies are extracted at `/home/nvidia/b12x-flare/deps`
from pinned packages; no system package installation or maintainer script runs.
Locked Python packages and Rust builds remain separate from the incumbent.

Before shutdown, snapshot both incumbent runtime trees, image identities and
unit/timer states into the candidate's private `local/` directory. Run incumbent
health and functional/speed smoke, retaining receipts as a prerequisite baseline;
the existing approximate c1 prefill script is not the full adoption matrix.
Disarm the incumbent watchdog, stop through `vllm-b12x.service`, verify both
containers gone, then require both hosts to reach 90 GiB MemFree and 100 GiB
MemAvailable before any build or GPU probe. Start builds through the candidate
user units. A head rollback timer must be armed before stopping production.

Pre-registered build gate: locked dependencies install, both Rust CLIs build,
and the pinned Torch stack passes compile/capture/replay on both GPUs without
driver changes. The small probe is not a substitute for exported-core replay,
model numerical tests or a performance comparison. Time budget: 90 minutes for
the build phase; automatic restoration at 120 minutes unless a later phase is
explicitly recorded with its own bounded timer before it begins.

On failure, stop candidate jobs on both nodes and invoke `flare_restore.sh`.
It starts the existing B12X unit, verifies health and restores the previously
active watchdog. Keep all candidate logs; do not change pins or relax gates
silently. A successful build proceeds to a separately recorded export/start
phase through candidate units. Export/native-start correctness failures require
restoration, not an adoption decision based on a short response.

Before any adoption decision, complete matched, exact-token prefill/decode
matrices at c1/2/4/8 (three reps), cold-cache evidence, reasoning/tools/cancellation,
exported indexer and KDA checks, and capacity qualification. Preserve the
incumbent baseline and never equate different engines' KV counters directly.

Research: [upstream issue 276](https://github.com/NVIDIA/hyperflare-inference/issues/276),
[preparation](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/model-preparation.md),
[multi-host](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/multi-host.md),
[Ubuntu extraction](https://ubuntu.com/project/docs/contributors/updating/extract-packages/).
Local sources reviewed: GLM recipe/gather and RoCE ABI, vLLM prefix benchmark,
EXL3 compiler setup, and TensorFold's observed-cache/token-count qualification.
