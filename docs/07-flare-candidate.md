# Flare candidate preparation tools

This lane prepares a reviewable alternative to the current vLLM B12X service.
It pins NVIDIA Flare and its FlashInfer dependency, renders separate TP2
preparation/serving commands, and inspects host readiness. It does not install,
stop or start services. Two-rank lifecycle management and complete native-model
qualification remain outstanding; rendered commands are not a production entry point.

## Candidate contract

`recipes/flare-glm53.json` pins the same NVIDIA checkpoint as the incumbent:
`76348ddb2be2e35e39ecfc00e75dc07703f4f3d5`. Flare is pinned at
`5a4e867954593b2e05bba43bc2a6eeaddca402d7`, with FlashInfer
`4fd836dcda0998b875129aad76774ca073df10c8`. Candidate files live under
`/home/nvidia/b12x-flare`; the incumbent remains `/home/nvidia/b12x`.

The first arm uses four slots, MTP-3 with fixed verification, 4096-token prefill,
text only and context parallelism disabled. It retains ordinary graphs for
correctness controls. The native API binds loopback port 8001 and preserves
`nvidia/GLM-5.3-Flash-FP4-Local` as its served alias. The preparation and serving
rendezvous ports are 29630 and 29800. This is an engine comparison; internal
arithmetic/scheduling differences must be measured, not attributed to one flag.

Flare prepares CUDA graphs with Ignition and serves exported cores through its
Rust runtime. The upstream GLM recipe supports this checkpoint and multi-host
TP2. [Preparation](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/model-preparation.md),
[multi-host serving](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/multi-host.md).

## Local review

```bash
uv sync --locked --python 3.12
uv run python scripts/flare_candidate.py render --rank 0
uv run python scripts/flare_candidate.py render --rank 1
uv run python -m unittest discover -s tests -v
```

Render prints JSON containing argv arrays, working directory, build environment,
configuration text and requirements. It performs no subprocess or network call.
The head serving command requires an explicit exported primary path; supply
`--core /absolute/path/model.safetensors` after export. The default placeholder
is deliberately unusable. Run build/preparation commands from the reported cwd
with the reported environment only after both nodes pass readiness checks.

Create the preparation token once and transfer it privately to the peer;
both copies must contain at least 32 random bytes and have mode 0600. Development
exports produce a signing key and public profile beside the explicit config.
Only the public profile goes to the peer. Approve the exact local-development
fingerprint on each rank before unattended serving; the renderer does not grant
blanket publisher trust. [Core signing](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/cli-design.md#signing-and-local-development).

## Readiness checks on an authorized Spark

```bash
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
uv run python scripts/flare_candidate.py inspect --rank 0
uv run python scripts/flare_candidate.py preflight --rank 0
```

Use rank 1 on the worker. `inspect` reports all facts and blockers with exit 0;
`preflight` exits nonzero if a blocker exists. Both are read-only. They check
memory, disk, required tools/development packages, indexed checkpoint files,
pinned clean source and dependency lockfiles. Driver identity is recorded;
this does not replace the CUDA compile/capture/replay compatibility probe.

Disk floors are conservative planning budgets: 250 GiB free on the head for the
core plus build/cache/staging space, 150 GiB on the peer for its rank data and
builds. They are not measured export sizes. Directory exports avoid the extra
packed-copy cost. Memory floors retain 90 GiB MemFree and 100 GiB MemAvailable
on each node. A resident production model is expected to fail these checks;
resolve disk/dependency blockers before scheduling its shutdown.

Native prerequisites include the CUDA toolkit/CUPTI, C/C++ tools, CMake, Ninja,
pkg-config, protoc, OpenSSL/Python/liburing/libibverbs development packages,
Rust and uv. The pinned environment uses PyTorch 2.14.1+cu132. R580 supports
CUDA 13.x minor compatibility with restrictions; PTX or newer features still
need a representative probe. Host driver/kernel changes require a separate
decision. [CUDA compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/latest/minor-version-compatibility.html).

## Speculative metrics

`scripts/speed_smoke.py --engine flare --base http://127.0.0.1:8001` selects native
Flare counters; the default remains vLLM. Both adapters require actual counter
samples, reject nonfinite values and counter resets, and compute run deltas.
Flare uses accepted draft tokens, proposed verification tokens and draft-bearing
request rounds, reporting `1 + accepted / rounds` and `accepted / proposed`.
Zero-draft request rounds are retained separately. [API metrics](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/api.md#health-and-metrics).

This change does not yet qualify the full engine comparison: the legacy speed
script still has approximate-length, c1-only prefill. Its existing absolute
`--gate` thresholds are historical B12X checks, not Flare adoption criteria.
Exact token fixtures, concurrent prefill, matched repeated-run comparisons,
native reasoning-template checks and full cache/state correctness remain required.

## Current qualification and rollback

The 2026-11-15 read-only inspection found the incumbent healthy on both Sparks,
with MTP-3, four slots, 1M context and the pinned image. The initial head disk budget failed; authorized housekeeping subsequently
raised free space to about 850 GiB head / 961 GiB worker. Retired DeepSeek
weights were removed with explicit permission; GLM and named rollback images
were retained. See `receipts/flare-housekeeping-20261115.json`. Both hosts lacked Ninja,
protoc and OpenSSL/liburing/Python development-package discovery. No production
stop, dependency install, candidate build or GPU qualification was performed.
Nine local tests passed; the vLLM adapter also parsed a live read-only scrape.

Checkpoint header inspection found all 42 indexed files (177,463,841,024 bytes),
42 CSF encoding declarations and the eleven target MLA absorption matrices in
BF16 in `tensors/native-QB.safetensors`. The MTP absorption and vocabulary head
have FP8 storage. `receipts/flare-checkpoint-metadata-20261115.json` records the
metadata hashes and declarations; this is not payload or numerical validation.

Upstream still lists GLM KDA reference and full-model numerical qualification
gaps. These require applicability analysis and passing evidence before adoption.
The historical exported-indexer corruption was fixed; preserve its reproducer
for larger speculative catalogs. [Upstream TODO](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/TODO.txt).

Return to the preserved source with `cd ../b12x`. For a future runtime rollback,
stop and confirm teardown of both candidate ranks, wait for both-node memory
recovery, then start the incumbent through `vllm-b12x.service`. Verify health
and functional smoke before restoring its watchdog and proxy. Retain snapshots,
images and checkpoint assets throughout the window. A Git checkout is not a
runtime rollback.
