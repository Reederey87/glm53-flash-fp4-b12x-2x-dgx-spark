# Candidate 3 — draft MoE Humming to b12x

Pre-registered before any restart. Final Astra sub-agent review is required
before this window is deployed. No automatic adoption.

## Treatment and research

Only `moe_backend` inside `--speculative-config` changes `humming` to `b12x`.
The complete candidate recipe differs from the control by that one string.
The existing `.env` source semantics select the committed recipe via `RECIPE`;
the append-only ledger is handed upstream through its last-wins projection.

Exa primary-source research: the
[NVIDIA same-checkpoint card](https://huggingface.co/nvidia/GLM-5.3-Flash-FP4-Local)
shows both the historical Humming launch and a newer b12x draft launch. The
newer launch changes many controls and is not copied wholesale. The separate
[NVFP4 checkpoint's BF16-MTP discussion](https://huggingface.co/nvidia/GLM-5.3-Flash-NVFP4/discussions/13)
does not establish the dtype of this pinned FP4-Local checkpoint. Direct header
inspection at `76348ddb` proves all864 layer45 routed-expert matrices have U8
packed weights,864 F8_E4M3 block scales and864 F32 global scales. Only423,888
header bytes were read, zero weight payload bytes. No weight payload is changed.

The installed image's unquantized oracle explicitly permits b12x to fall through
to auto, unlike the current local vLLM source. Its ModelOpt NVFP4 method prepares
b12x expert layouts. Backend support must be proved by this image's actual
startup and resolved configuration, not inferred from newer source alone.
FlashInfer's fused-MoE packed-source contracts, local vLLM speculative overrides,
EXL3 recurrent checkpoint lifetimes, Flare's prepared MTP scratch/weights and
TensorFold's memory-profile guidance were reviewed. Adopt TensorFold's applied
profile/phase receipts and exact budgets in the current trial; do not port its
engine or spill features. Requantized drafts, adaptive depth, draft-head changes
and newer engine/images are stronger but separate treatments and remain frozen.

## Frozen controls

- Both nodes: image ID `3b5da79c42ed4204440cfb07c6de1eba46441d5cba6b57d5428d44e60c10d0ed`.
- Checkpoint `76348ddb2be2e35e39ecfc00e75dc07703f4f3d5`; no requantization.
- TP2/RoCEnante, target MoE/linear/attention b12x; draft attention B12X, MTP3.
- 17G FP8 KV, block256, expected pool2,350,210; four seats; context1,000,000;
  batched4096; prefix cache and chunked prefill; default allocator on both ranks.
- Same driver, checkpoint, OS, kernel, image, prompts, seeds, output budgets,
  measurement code, concurrencies and fresh process/cache policy in both arms.

## Gates and measurement

1. Fresh restart for **both** A and B through `vllm-b12x.service`. Unit memory
   gate still requires >=90 GiB free/>=100 GiB available on both nodes.
2. Independent observer stops production below2 GiB host MemAvailable, or on
   failed/malformed probes. Invocation-bound readiness and age0..20s are checked
   during startup and measurement. Observability is the same in both arms.
3. Stop/assert inactive watchdog timer, executing watchdog and external proxy.
   Arm independent recovery before the first service change. Snapshot ledger,
   recipes, code hashes, images and rank profiles. Stage atomically as nvidia.
4. Actual image and rank argv/env must show the selected backend, k3, default
   allocator and every frozen control. Capture profiles and boot logs during
   startup, before health. Health within the existing900s unit health gate;
   expected KV pool, and all five functional smoke checks must pass. Both rank
   boot logs must contain the pinned oracle's resolved `Using 'HUMMING'` or
   `Using 'B12X' NvFp4 MoE backend` selection as appropriate. B rejects any
   Humming selection/config initialization; requested argv alone cannot qualify.
5. Each arm: three temperature0 parity prompts; raw8k probe; then full exact
   8192/16384/32768/65536/131072 cold ladder at c1/2/4/8 and200-token decode
   budget, three reps per concurrency. Report four-seat cap at c8. All cold
   counts must be0; preserve partial receipts on failure.
6. Both arms repeat twelve decode batches **after** the ladder; comparison uses
   those post-ladder batches and matched prefill rows. Preserve originals and
   hashes. Require complete per-request usage/DONE/TTFT/timing, finite observed
   counter snapshots and unchanged API/engine/rank PIDs throughout each batch.
7. Eligible for adoption review only if c1 or c8 median aggregate decode is
   >=2% faster, no robust >2% regression at any prefill/decode cell or acceptance
   rate/length, and no correctness/capacity loss. Flagged/noisy cells require
   matched repetitions before a robust speed verdict. Flat results are not a
   demonstrated improvement. Parity divergences are retained and reviewed;
   code/math answers must be substantive and structured weather tools valid.
8. A failure to start or an observer abort is a failed qualification, with no
   B throughput claim if the matrix is incomplete. Never force an unsafe arm
   through the matrix merely to collect numbers.

## Recovery and delivery

`b12x-recipe-window@draft-b12x.service` uses mixed termination and a serialized
ExecStopPost recovery hook, including after a killed parent. Every finish
restores the original control recipe/image and default allocator by appending,
then checks both actual rank profiles/images, smoke5/5 and health200. External
traffic reopens only after validation; each unit is checked independently.
Primary and recovery status are separate. Runtime dir `local/ab-draft-b12x/`.
Do not modify an executing script in place. Update changelog/TODO and PR after
cluster receipts, and ask before any permanent adoption.
