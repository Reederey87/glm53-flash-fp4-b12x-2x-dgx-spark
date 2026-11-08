# Credits

This kit is largely an integration. Almost everything that does heavy work was
written by someone else; the sections below say exactly who, under which terms,
and how this repository uses it. If a statement here and an upstream license
disagree, the upstream license wins.

The kit itself (scripts, systemd units, recipe, documentation) is
**Apache-2.0**, copyright 2026 Reederey87 — see [LICENSE](LICENSE) and
[NOTICE](NOTICE).

## What this repository does *not* redistribute

- Model weights (`nvidia/GLM-5.3-Flash-FP4-Local`, ~166 GiB).
- The container image `vllm-node-b12x` (~tens of GiB).
- Upstream source trees (`vllm`, `flashinfer`, `spark-vllm-docker`, Flare).

The launcher clones `spark-vllm-docker` into `.vendor/` on the target host at a
pinned commit (`.gitignore`d); the image and weights are pulled or staged on the
Sparks. Receipts under `receipts/` are measurements, not distributions of
upstream code.

## Engines and kernels

| Work | Author / project | License | How this kit uses it |
|---|---|---|---|
| [vLLM](https://github.com/vllm-project/vllm) | the vLLM project | Apache-2.0 | The inference engine in the pinned image: scheduler, prefix cache, chunked prefill, OpenAI API, MTP speculation, `glm45`/`glm47` parsers. Not modified by this kit. |
| [FlashInfer](https://github.com/flashinfer-ai/flashinfer) | FlashInfer project | Apache-2.0 | Kernel layer in the image, including the `b12x` package under `flashinfer/experimental/b12x`. |
| [b12x](https://github.com/local-inference-lab/b12x) | local-inference-lab contributors | Apache-2.0 | SM120/SM121 kernel library: NVFP4/MXFP8 GEMM, fused MoE, sparse/compressed MLA, `--load-format b12x`, RoCEnante collectives (`comm.roce`). Now vendored in FlashInfer; this kit runs that copy rather than a separate package. |
| [eugr/spark-vllm-docker](https://github.com/eugr/spark-vllm-docker) | Eugene Rakhmatulin | **MIT** | Docker orchestration for DGX Spark. `launch.sh` clones it at `0bdc9c94…` into `.vendor/` and runs `run-recipe.sh` / `launch-cluster.sh`. The recipe file format and several serving flags follow it. |
| Image `eugr/spark-vllm-b12x` | built from the two projects above | image terms | Pulled (or reused locally) and pinned by digest. The kit does not rebuild or redistribute it. The image also bundles components beyond the list above (CUDA, PyTorch, transformers, humming, tilelang, …), each under its own license. |

## Model and prompt format

| Work | Author | License | How this kit uses it |
|---|---|---|---|
| [`nvidia/GLM-5.3-Flash-FP4-Local`](https://huggingface.co/nvidia/GLM-5.3-Flash-FP4-Local) | NVIDIA Corporation | [NVIDIA Open Model Agreement](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-agreement/) | The served checkpoint and its chat template. The recipe's flags come from the model card's **2 × DGX Spark** command; the reasoning-default contract follows the checkpoint template. Weights are downloaded by the operator, never included here. |
| [GLM-5.3-Flash](https://huggingface.co/zai-org/GLM-5.3-Flash) | Z.ai / Zhipu AI | MIT | The base model the checkpoint quantizes. |
| Model Optimizer (QAD) | NVIDIA | Apache-2.0 | Produced the checkpoint's quantization; cited in the model card, not run by this kit. |

## Consulted for qualification (no code copied)

| Work | Author | License | How this kit uses it |
|---|---|---|---|
| [NVIDIA Flare (`flare-local-inference`)](https://github.com/NVIDIA/flare-local-inference) | NVIDIA Corporation | Apache-2.0 | Its `glm53` recipe pins the same checkpoint revision, which is how this kit establishes that Flare now supports the checkpoint. Its published TP2 capacity and package-size figures are cited in `docs/01-qualification.md` as *Flare's* numbers, not measurements from this pair. No Flare code is copied or executed by the kit. |

## Derived from the author's earlier kit

| Work | Author | License | How this kit uses it |
|---|---|---|---|
| [`Reederey87/glm53-flash-exl3-2x-dgx-spark`](https://github.com/Reederey87/glm53-flash-exl3-2x-dgx-spark) | Reederey87 | Apache-2.0 | `scripts/watchdog.sh` and `scripts/tailscale_proxy.py` are adapted from that kit's runtime tree, as are the unit shape (oneshot + `RemainAfterExit`, health gate, two-node memory gate) and the preflight/smoke conventions. Retargeted to `vllm-b12x.*` and the 90 GiB `MemFree` / 100 GiB `MemAvailable` gate. |

## Measurement sources

- The serving matrix in `docs/03-gate.md` follows the workspace's speed-smoke
  procedure: cache-cold prefill at 8k/16k/32k/64k/128k, decode with speculative
  acceptance at concurrency 1/2/4/8.
- The `2,350,210` KV-token figure and the `~2.3k tok/s` prefill band are this
  pair's own receipts (`receipts/speed-*.json`). Flare's `~1.1M` figure is
  credited to Flare and labelled as such wherever it appears.

## If you reuse this kit

Keep `LICENSE`, `NOTICE` and this file. If you redistribute the image or the
weights, their terms apply on top of this kit's Apache-2.0 — in particular the
NVIDIA Open Model Agreement for `nvidia/GLM-5.3-Flash-FP4-Local`, and the MIT
terms for `spark-vllm-docker` if you vendor it rather than clone it.
