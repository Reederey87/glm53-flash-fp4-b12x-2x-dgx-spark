# Alternatives — the same checkpoint on two Sparks

Surveyed 2026-11-08 with the Exa MCP search and each project's own files. Scope:
**only kits that serve `nvidia/GLM-5.3-Flash-FP4-Local` on two DGX Spark
(GB10) nodes.** Kits for the NVFP4, EXL3 or 3-bit checkpoints are a different
quant and are listed at the end; they are not part of the comparison.

## At a glance

| Kit | Engine | Context / KV | Seats / speculation | Operations | Licence |
|---|---|---|---|---|---|
| **this kit (`b12x`)** | vLLM B12X, pinned digest `3b5da79c` | **1M / 2.35M tok** | 4 / MTP-5 | systemd, boot-verified, watchdog, tailnet | Apache-2.0 |
| [myllmbox recipe](https://github.com/myllmbox/glm53-flash-cluster-recipe) | vLLM 0.32 + own `mbx` loader | 400k / 1.15M tok | **16** / MTP 1–9 dynamic | `run.sh`, optional host tuning | MIT |
| [Flare guide](https://github.com/gpdev-Pilcothink/flare-spark) | Flare native (Python prep → Rust serve) | 1M / **3.4–4.8M tok** | **12** / MTP-5 | shell launcher, >1 h first preparation | Apache-2.0 |
| [Enntity/SparkGLM](https://github.com/Enntity/sparkglm) | Atlas (own engine) | 4 × 1M profile / ~2.66M | 4 / DFlash2 or native MTP | `start.sh`, clock-cap required, TP2/TP4 | **AGPL-3.0** + **CC BY-NC-ND** drafter |
| [eugr/spark-vllm-docker](https://github.com/eugr/spark-vllm-docker) | vLLM B12X, moving nightly | 500k / 8 GiB | 4 / MTP-5 | one-step launcher, no service | MIT |
| [NVIDIA DGX Spark playbook](https://github.com/NVIDIA/dgx-spark-playbooks) | same image `nightly-20261015` | 500k / recipe default | 4 / MTP-5 | manual two-rank launch or launcher | NVIDIA playbook |
| [DevelopingDad recipe](https://huggingface.co/DevelopingDad/GLM-5.3-Flash-FP4-Local-DGX-Spark-Optimized) | vLLM + 4 engine patches | 262k / 808k tok | 4 / adaptive MTP | Python launcher, 8 GiB guard, **no boot persistence** | Apache-2.0 |

## What each is better at

- **myllmbox** — the fastest published single-stream and multi-stream numbers on
  this checkpoint: 45 tok/s average / 87 peak thinking-on at c=1, 214 tok/s peak
  at 16 streams, 1,836 tok/s prefill at 128k, 16 seats. Costs: 400k context,
  1.15M pool, a custom loader image and Marlin-based expert path.
- **Flare** — the largest native KV cache here (16 GiB → **4.78M** tokens; 11.8
  GiB → 3.44M), 12 seats, 1M prepared context, comparable decode (37–42 tok/s in
  its guide), lower prefill (~1.5k tok/s). Costs: a first preparation that can
  take over an hour and a prepared package on disk.
- **eugr/spark-vllm-docker** — the reference the model card points to; newest
  recipes and image tags, least code. A launcher, not a deployment: moving tags,
  no unit, no watchdog, no receipts.
- **NVIDIA DGX Spark playbook** — the official reproducibility write-up of the
  same recipe, with a published SPEED-Bench decode figure of 33.94 tok/s.
- **Enntity/SparkGLM** — the most engineered alternative: own engine, prefix
  cache on disk, KV sharding, display-carveout memory, TP4 chain/ring, and the
  only published TP2 RigMark numbers that beat this stack (prose 37.0, code 67.9,
  structured 90.8 tok/s at low effort). Costs: different engine, `clock-cap`
  prerequisite, AGPL-3.0 and a non-commercial DFlash2 drafter.
- **DevelopingDad** — the best measured *relative* throughput gain on the same
  image family: +23.43 % short/concurrent from four reviewable patches, MTP only,
  Apache-2.0. Costs: 262k context and an 808k pool, plus a launcher that installs
  no boot persistence.

## Where this kit wins

- **It is a service, not a launcher.** Only this kit ships a systemd unit, a
  two-node 90 GiB MemFree / 100 GiB MemAvailable gate, a bounded watchdog, a
  tailnet proxy, and a boot auto-start proven by a real two-node power cycle
  (`receipts/boot-20261108-second.txt`). Every other entry starts a container
  from a shell.
- **Pinned and checked bytes** — image digest, checkpoint revision, launcher
  commit and FlashInfer build are recorded and re-checked by `preflight` and
  `qualify`.
- **The largest pool among the vLLM recipes** — 2.35M tokens at 1M context,
  against 500k/8 GiB (eugr, NVIDIA), 262k/808k (DevelopingDad) and 400k/1.15M
  (myllmbox). Flare's native cache is larger; state that plainly.
- **An asserted reasoning contract** — a request without `reasoning_effort`
  renders `Reasoning Effort: Max`, and `smoke` fails if that drifts.
- **Permissive licensing** — Apache-2.0, no AGPL engine, no non-commercial
  drafter.
- **Least machinery** — no custom loader, no patch tooling, no >1 h preparation,
  no clock cap; stdlib-only scripts and one command to a healthy endpoint.

## Where this kit is behind

- **Capacity and seats.** Flare holds 3.4–4.8M KV tokens and 12 seats; myllmbox
  holds 16 seats. This kit has 2.35M and 4.
- **Single-stream speed.** myllmbox publishes 45 tok/s average at c=1; this kit's
  own cache-cold matrix measures 27.8 (different harness, but the gap is large
  enough to investigate).
- **Features.** No DFlash2, no disk KV tier, no display-carveout memory, no TP4.
- **Freshness.** The image was built 2026-11-03; upstream nightlies move, and its
  FlashInfer is 140 commits behind the workspace clone (`91271757` vs `361e45fa`).

## Read the numbers carefully

Every project measured on its own pair, with its own prompts, reasoning effort
and output budget: this kit uses cache-cold unique prompts, a 200-token budget
and the checkpoint's Max reasoning default; myllmbox sustains 300 s streams at
16 seats; Flare reports llama-benchy tg128/tg1024; SparkGLM uses RigMark at low
effort; DevelopingDad 512-token requests; NVIDIA SPEED-Bench. **Only numbers from
the same harness are comparable.** Cross-kit figures choose what to test next;
they do not rank the kits.

## Adjacent kits (different checkpoint, not compared)

`barrydeen/glm53-flash-dgx-spark`, `himorishige/glm53-flash-2x-dgx-spark-recipe`,
`tonyd2wild/GLM-5.3-Flash-NVFP4-DFlash2-2x-DGX-Spark`,
`0rand/glm-5.3-flash-nvidia-nvfp4-dflash-2x-dgx-sparks`,
`mazar/spark-glm53`, `LimeChain/glm-5.3-flash-2xdgx-spark`,
`Plaaasma/glm53-flash-dual-dgx-spark`, `alexellis/glm-5.3-flash-2x-dgx-spark-switchless`
(NVFP4, but the closest operational peer: systemd unit, health gates, cache
persistence), `MiaAI-Lab/...-EXL3-...-TensorFold`,
`strusty/GLM-5.3-Flash-NVFP4-3x-DGX-Sparks-kindling-DGXOS` (TP3). They target
NVFP4 or EXL3 weights, so their speed and quality numbers do not transfer to
this checkpoint, and this kit's do not transfer to them.

## Sources

- Model card and 2× Spark command: <https://huggingface.co/nvidia/GLM-5.3-Flash-FP4-Local>
- Reference launcher: <https://github.com/eugr/spark-vllm-docker>
- NVIDIA playbook: <https://github.com/NVIDIA/dgx-spark-playbooks> and
  <https://build.nvidia.com/playbooks/vllm-cluster/advanced>
- myllmbox: <https://github.com/myllmbox/glm53-flash-cluster-recipe>
- Flare guide: <https://github.com/gpdev-Pilcothink/flare-spark> (GLM53-Flash
  guide; 4,782,080 KV tokens at 16 GiB, 3,439,616 at 11.8 GiB)
- SparkGLM: <https://github.com/Enntity/sparkglm> (AGPL-3.0; DFlash2
  CC BY-NC-ND 4.0)
- DevelopingDad: <https://huggingface.co/DevelopingDad/GLM-5.3-Flash-FP4-Local-DGX-Spark-Optimized>
- Flare: <https://github.com/NVIDIA/flare-local-inference>
