# Pre-registered gate — first b12x window (2026-11-08)

Written **before** the swap. A gate written after the numbers is not a gate.

## Independent variable

The runtime tree and its contract: the `b12x` kit (own launcher, pinned image
digest, pinned checkpoint revision, explicit max-reasoning default) replaces the
incumbent `glm53-fp4-local` tree.

## Frozen controls

| Control | Value |
|---|---|
| image | `sha256:3b5da79c42ed…` (`vllm-node-b12x`), unchanged |
| checkpoint | `76348ddb2be2e35e39ecfc00e75dc07703f4f3d5`, unchanged |
| KV | `--kv-cache-memory-bytes 17G`, fp8, block 256 |
| scheduler | `max-num-seqs 4`, `max-num-batched-tokens 4096`, chunked prefill, prefix cache |
| speculation | MTP-5, humming MoE, B12X attention |
| context | `--max-model-len 1000000` |
| collectives | RoCEnante 2 MB AR / 16 MB AG |
| hardware | same two Sparks, same fabric, no driver change |

## Hard gates (all must pass)

| # | Gate | Threshold | Signal |
|---|---|---|---|
| 1 | boot health | `/health` 200 within 900 s | unit `ExecStartPost` |
| 2 | served id | `nvidia/GLM-5.3-Flash-FP4-Local` | `/v1/models` |
| 3 | context | `max_model_len == 1000000` | `/v1/models` |
| 4 | KV pool | `≥ 2,300,000` FP8 tokens | boot log `GPU KV cache size` |
| 5 | functional | every hard check in `smoke.py` passes | `receipts/` |
| 6 | reasoning default | request without `reasoning_effort` renders `Reasoning Effort: Max` | `verify_reasoning.py` |
| 7 | prefill | `≥ 1,500 tok/s` at 8k **and** 128k (cache-cold, c=1) | `speed_smoke.py` |
| 8 | decode c=1 | `≥ 25 tok/s` | `speed_smoke.py` |
| 9 | decode c=8 | `≥ 55 tok/s` aggregate | `speed_smoke.py` |
| 10 | acceptance | accept length `≥ 2.0`, draft accept rate `≥ 0.25` | `vllm:spec_decode_*` deltas (baseline `speed-20261108T133210Z`) |

> Amended 2026-11-08 before the swap, from the incumbent baseline only (no
> candidate numbers existed): c=8 measured 59.1–60.2 tok/s aggregate and the
> draft accept rate 0.288–0.31. Thresholds of 60 and 0.35 would have gated on
> noise.
> 55 rejects a real regression and leaves the measured baseline as the
> reference point in `receipts/speed-20261108T133210Z.md` (clean, cache-cold).

## Soft signals (recorded, not gating)

- decode at c=2 and c=4 per-request, TTFT at 8k/32k/128k.
- `MemAvailable` after boot on both nodes (must be > 2 GiB; warn under 5 GiB).
- async-scheduling state in the boot log (not passed explicitly on this build).

## Decision

- **Adopt** if gates 1–10 pass. Keep the incumbent tree and image on disk.
- **Revert** on any hard gate miss: `systemctl --user stop vllm-b12x.service`,
  re-enable `vllm-glm53fp4.service`. The image and checkpoint are unchanged, so
  rollback is a unit swap, not a rebuild.
- One treatment per window. Do not tune a knob to rescue a miss in the same
  window; record it and open the next window.
