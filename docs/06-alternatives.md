# Alternatives — the same checkpoint on two Sparks

Surveyed 2026-11-08 with the Exa MCP search and each project's own files. Scope:
kits that serve **`nvidia/GLM-5.3-Flash-FP4-Local`** on **two DGX Spark (GB10)**
nodes. Kits for the NVFP4, EXL3 and 3-bit DeepSeek checkpoints are a different
quant and are excluded from the table (they are listed at the end).

## At a glance

| Kit | Engine | Context / KV | Speculation | Operations | Licence |
|---|---|---|---|---|---|
| **This kit (`b12x`)** | vLLM B12X, pinned digest `3b5da79c` | **1M / 17 GiB → 2,350,210 tok** | MTP-5 | systemd unit, boot-verified, watchdog, tailnet proxy | Apache-2.0 |
| [`eugr/spark-vllm-docker`](https://github.com/eugr/spark-vllm-docker) | vLLM B12X, moving nightly | 500k / 8 GiB (recipe default) | MTP-5 | one-step `run-recipe.sh`; no service management | MIT |
| [NVIDIA DGX Spark playbook](https://github.com/NVIDIA/dgx-spark-playbooks) | same image `nightly-20261015` | 500k / recipe default | MTP-5 | manual two-rank launch or launcher; `--no-build` | NVIDIA playbook |
| [Enntity/SparkGLM](https://github.com/Enntity/sparkglm) | **Atlas** (own engine) | 4 × 1M profile; ~2.66M pool (historical) | DFlash2 or native MTP | `start.sh`, clock-cap service, TP2/TP4 | **AGPL-3.0**; drafter **CC BY-NC-ND** |
| [DevelopingDad recipe](https://huggingface.co/DevelopingDad/GLM-5.3-Flash-FP4-Local-DGX-Spark-Optimized) | vLLM + 4 engine patches, image `03a956…` | 262,144 / 8 GiB → 808,020 tok | adaptive MTP | Python launcher, 8 GiB memory guard; **no boot persistence** | Apache-2.0 |
| [NVIDIA Flare](https://github.com/NVIDIA/flare-local-inference) | Flare (Python prep → Rust serve) | ~1.1M KV (Flare's own TP2 figure) | native | `orbit run`, package preparation | Apache-2.0 |

## What each is better at

- **eugr/spark-vllm-docker** — the reference the model card points to. Newest
  recipes and image tags, least code of all. It is what this kit pins and
  wraps; its weakness is that it is a launcher, not a deployment: moving tags,
  no unit, no boot/watchdog, no receipts.
- **NVIDIA DGX Spark playbook** — the official, reproducibility-oriented write-up
  of the same recipe, with a published SPEED-Bench decode figure of
  33.94 tok/s (measured 2026-10-16). Best starting point if you want NVIDIA's
  documentation and nothing else.
- **Enntity/SparkGLM** — the most engineered alternative: own engine, prefix
  cache on disk, KV sharding across the two Sparks, display-carveout memory,
  1M-token profiles, TP4 chain/ring, and the only published TP2 RigMark decode
  numbers that beat this stack (prose 37.0, code 67.9, structured 90.8 tok/s at
  low effort). Costs: different engine, `clock-cap` prerequisite, AGPL-3.0 and
  a **non-commercial** DFlash2 drafter.
- **DevelopingDad recipe** — the best measured *throughput* result on the same
  checkpoint and image family: +23.43 % on short/concurrent requests from four
  reviewable vLLM patches, Apache-2.0, MTP only. Costs: 262k context and an
  808k-token pool (a quarter of this kit's), plus a launcher that installs no
  boot persistence.
- **NVIDIA Flare** — the official engine, smallest request path (no Python at
  serve time). Costs: a multi-hour, ~178 GB package preparation and roughly half
  this stack's KV capacity on the same pair.

## Where this kit wins

- **Capacity at full window** — 1M context with a 2.35M-token FP8 pool, versus
  262k/808k for the patched recipe and 500k/8 GiB for the reference recipes.
- **Production behaviour** — systemd unit with a two-node 90 GiB MemFree /
  100 GiB MemAvailable gate, a bounded watchdog, and a boot auto-start that was
  proven by a real two-node power cycle (`receipts/boot-20261108-second.txt`).
  None of the other kits ship this.
- **Pinned bytes** — image digest, checkpoint revision, launcher commit and
  FlashInfer build are all recorded and checked by `preflight`/`qualify`.
- **Licensing** — Apache-2.0 across the kit, no non-commercial drafter, no
  copyleft engine.
- **Evidence** — cache-cold prefill ladder, decode matrix with speculative
  acceptance, functional smoke including the reasoning default, and the
  qualification receipt, all in-repo.

## Where this kit is behind

- It does not carry the DevelopingDad patchset (+23 % short/concurrent on their
  pair) or Enntity's DFlash2 and cache tiering. Adopting either is a separate,
  pre-registered window — see `spec/TODO.md`.
- The pinned image was built 2026-11-03; upstream nightlies move, and its
  FlashInfer is 140 commits behind the workspace clone (`91271757` vs `361e45fa`).
- Decode at c=1 is below Enntity's published RigMark prose figure. The two were
  not measured with the same harness, reasoning effort or output budget, so this
  is a pointer to investigate, not a like-for-like loss.

## Read the numbers carefully

Every project above measured on its own pair, with its own prompts, reasoning
effort and output budget: this kit uses cache-cold unique prompts with a
200-token budget and the checkpoint's Max reasoning default; Enntity uses
RigMark with low effort; DevelopingDad uses 512-token requests including
reasoning; NVIDIA uses SPEED-Bench. **Only numbers from the same harness are
comparable.** Cross-kit figures here are for choosing what to test next, not for
ranking.

## Adjacent kits (different checkpoint, not compared)

`barrydeen/glm53-flash-dgx-spark`, `himorishige/glm53-flash-2x-dgx-spark-recipe`,
`tonyd2wild/GLM-5.3-Flash-NVFP4-DFlash2-2x-DGX-Spark`,
`0rand/glm-5.3-flash-nvidia-nvfp4-dflash-2x-dgx-sparks`,
`mazar/spark-glm53`, `LimeChain/glm-5.3-flash-2xdgx-spark`,
`Plaaasma/glm53-flash-dual-dgx-spark`, `MiaAI-Lab/...-EXL3-...-TensorFold`,
`strusty/GLM-5.3-Flash-NVFP4-3x-DGX-Sparks-kindling-DGXOS` (TP3). They target
NVFP4 or EXL3 weights, so their speed and quality numbers do not transfer to
this checkpoint, and this kit's do not transfer to them.

## Sources

- Model card and 2× Spark command: <https://huggingface.co/nvidia/GLM-5.3-Flash-FP4-Local>
- Reference launcher: <https://github.com/eugr/spark-vllm-docker>
- NVIDIA playbook: <https://github.com/NVIDIA/dgx-spark-playbooks> and
  <https://build.nvidia.com/playbooks/vllm-cluster/advanced>
- SparkGLM: <https://github.com/Enntity/sparkglm> (AGPL-3.0, DFlash2
  CC BY-NC-ND 4.0)
- DevelopingDad: <https://huggingface.co/DevelopingDad/GLM-5.3-Flash-FP4-Local-DGX-Spark-Optimized>
- Flare: <https://github.com/NVIDIA/flare-local-inference>
