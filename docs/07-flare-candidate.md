# Flare candidate preparation tools

> Historical architecture or qualification record. Current production, unresolved gates and the research pause: [docs/63](63-production-pause-checkpoint.md). Old window controllers must be adapted before reuse.

This lane prepares a reviewable alternative to the current vLLM B12X service.
It pins NVIDIA Flare and its FlashInfer dependency, renders separate TP2
preparation/serving commands, and inspects host readiness. Candidate-only systemd units build, prepare and
serve through a two-rank coordinator. Native-model qualification is still a
required gate; installation of the units does not qualify the model.

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

The current candidate also enables `native_dense_activations` during export.
This supported preparation option passed the registered KDA component bounds;
it does not turn the model into an unquantized checkpoint or qualify all numerical
paths. The original auto-precision core and its failed KDA receipts are retained.

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

`flare_bench.py` adds exact raw-token cold prefill at c1/2/4/8 and matched
code/prose decoding, observed cache counts and run-local speculative counters.
Both arms use temperature 1 and top-p .95 because the Flare core does not preserve greedy temperature-zero semantics.
`flare_smoke.py` checks native prompt tokens, reasoning, tools, structured output,
prefix reuse and cancellation. These tools still require native hardware receipts.
The legacy speed script is a health reference, not a fair Flare speed comparison.

## Current qualification and rollback

The 2026-11-15 read-only inspection found the incumbent healthy on both Sparks,
with MTP-3, four slots, 1M context and the pinned image. The initial head disk budget failed; authorized housekeeping subsequently
raised free space to about 2,837 GiB head / 2,947 GiB worker after two cleanup waves. Explicitly
approved retired DeepSeek V4/V4.1, MiMo, Inkling and previous GLM EXL3 weights
were removed; the current NVIDIA GLM checkpoint and named rollback images
were retained. See `receipts/retired-models-cleanup-20261115.json`. Both hosts initially lacked native development prerequisites. The authorized
trial extracted pinned Ubuntu packages into candidate-owned `deps/`, installed
the locked preparation environment, and built the native CLI on both nodes.
Both SM121 CUDA compile/capture/replay probes passed on the existing driver.
The worker uses the same uv-managed CPython 3.12.14 as the head. Candidate cache
paths are isolated from root-owned production container caches. Fifteen local
tests passed at that prerequisite stage; the current kit has 40 passing local
tests. The subsequent native-activation export passed startup and all seven API
checks, and its component window passed 49 cases without skips. Full-model
quality, capacity, lifecycle and the complete speed comparison remain separate;
see
`08-flare-build-window.md` and `09-flare-export-gate.md` for the trial contract.

Checkpoint header inspection found all 42 indexed files (177,463,841,024 bytes),
42 CSF encoding declarations and the eleven target MLA absorption matrices in
BF16 in `tensors/native-QB.safetensors`. The MTP absorption and vocabulary head
have FP8 storage. `receipts/flare-checkpoint-metadata-20261115.json` records the
metadata hashes and declarations; this is not payload or numerical validation.

Upstream still lists GLM KDA reference and full-model numerical qualification
gaps. These require applicability analysis and passing evidence before adoption.
The historical exported-indexer corruption was fixed; preserve its reproducer
for larger speculative catalogs. [Upstream TODO](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/TODO.txt).

Return to the preserved source with `cd ../b12x`. For runtime rollback,
stop and confirm teardown of both candidate ranks, wait for both-node memory
recovery, then start the incumbent through `vllm-b12x.service`. Verify health
and functional smoke before restoring its watchdog and proxy. Retain snapshots,
images and checkpoint assets throughout the window. A Git checkout is not a
runtime rollback.

## Candidate lifecycle

`scripts/flare_native_deps.sh` extracts exact package versions without changing
system packages. Source `flare_env.sh` only in candidate processes. The build
units verify clean pinned sources and dependency locks, compile the CLI, run
the CUDA probe and record binary/lock hashes. The prepare unit coordinates
rank 1; export is never implicit in a serving start. The serving wrapper verifies
the accepted core and public signing fingerprint, propagates peer failures and
bounds readiness. Services have no automatic restart.

### Accepting the exact new export

A successful head preparation unit prints `Export provenance awaiting acceptance`
with a unique `local/export-rank0-<id>.json` path. Both preparation ranks must have
exited successfully before proceeding. That receipt records the new primary's
hash, resolved plan, export argv and source pins. Use the receipt from that exact
completed export, not whichever log happens to be newest.

Inspect the primary with the pinned native CLI and the explicit public profile:

```bash
cd /home/nvidia/b12x-flare
source scripts/flare_env.sh
upstream/flare/flare-cli/target/release/flare inspect /absolute/export/path/model.safetensors \
  --json --graphs --publisher-keys development-publisher.json \
  --trust-store trust.toml --core-cache cores > local/reviewed-core-inspect.json
```

Require verified signatures, the intended core ID, both SM121 ranks and the
registered model, graph catalog, context, concurrency and speculation settings.
Review the resolved plan in the local export receipt as well: this pin's signed
rebuild metadata does not attest to `native_dense_activations`. The receipt is
unsigned local provenance, supplementing signature verification. Full payload
verification runs again at native startup through `--verify-weights`.

After this review, snapshot any previous acceptance file and prepare
`local/accepted-core.json` with these fields:

| Field | Value to record |
| --- | --- |
| `core_primary` | Absolute new primary path under the isolated `cores/` tree |
| `core_primary_sha256` | SHA256 of that primary, matching the export receipt |
| `core_id` | Core ID from verified native inspection |
| `publisher_profile_sha256` | SHA256 of the exact `development-publisher.json` bytes |
| `key_fingerprint` | SHA256 of the profile's 32 public-key bytes; exactly one `local-development` profile |
| `export_receipt` | Absolute matching receipt path under the candidate's `local/` directory |
| `export_receipt_sha256` | SHA256 of that exact receipt file |

Transfer the public profile, accepted state and export receipt to the same paths
on the worker. Stage temporary files and rename them atomically; preserve the
previous acceptance snapshot. The primary path identifies the head's export;
the peer obtains its rank payloads through the native distribution protocol.
Never transfer the private signing key. Acceptance of this locally generated
key is distinct from an authenticated NVIDIA publisher identity, as described
in the [upstream signing contract](https://github.com/NVIDIA/hyperflare-inference/blob/main/docs/cli-design.md#signing-and-local-development).

The serving wrapper rejects missing or changed provenance, wrong primary/profile
hashes, mismatched pins or a different resolved preparation plan. A successful
guard check still does not replace native signature/payload verification or the
hardware qualification gates. Start only through the head serving unit after
the registered snapshots, timer and memory checks; do not execute the renderer's
bare serving argv as a deployment entry point.

Start the head `b12x-flare-build@0.service` and worker build rank 1 independently
after the window gates. Then start head `b12x-flare-prepare@0.service`. Only after
core acceptance, start head `b12x-flare@0.service`. Do not enable candidate units
at boot during trials. `scripts/flare_restore.sh` stops all candidate phases on
both nodes, releases completed candidate core file pages, starts
`vllm-b12x.service` through its unchanged memory gate, verifies health and restores
its watchdog. See [the first trial](11-flare-trial-20261115.md) for measured results.
A pre-armed transient timer invokes this restoration if the trial overruns.

Never publish `checkpoint.token`, the development signing key, runtime environment
snapshots or raw container inspections. Transfer only the public publisher profile.

## Qualification and serving reserve arms

`b12x-flare-qualify@.service` builds the pinned qualification-only extension into
an isolated import path, then runs native indexer replay and KDA state bounds.
It must run only in an idle-cluster window with timed rollback; it never installs
that extension into the ordinary preparation environment. The restore helper
stops qualification units before memory recovery. The first numerical window
failed its KDA bound; the subsequent native-activation arm passed all 49 cases
under the original bounds. See the qualification gate and retained receipts.

Serving reads only `FLARE_SERVE_RESERVE_GIB=<positive integer>` from the runtime
`.env` ledger; the last assignment wins. Other ledger entries are not executed
or imported. With no assignment, serving retains the recipe's 4 GiB reserve.
This control does not change export configuration, checkpoint, graph catalog or
accepted core. Do not source the ledger as a shell script. A proposed 3 GiB arm
and its rejection/rollback criteria are in [the next gate](12-flare-qualification-gate.md).
