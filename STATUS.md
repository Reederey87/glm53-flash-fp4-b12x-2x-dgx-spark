# Status

## 2026-11-15 — Indexer replay qualified; KDA error begins in projection

- Diagnostic kit e8b6ac0 passed all four SM121 indexer replay cases after using
  production MLA's mixed-projection factory; 12 weight and 31 state checks also
  passed. Both original KDA graph errors reproduced exactly. The first observed
  discrepancy was input projection: relative L2 .02567028 TP2 / .02558133 TP4,
  before convolution/recurrence. Diagnostic output error matched the original
  graph measurement; observations alone do not establish a serving fix.
- Restored B12X at 21:58:08 UTC; smoke5/5 at 21:58:36, unchanged image identities,
  watchdog/tailnet active, safety timer disarmed. Receipt:
  `receipts/flare-qualification-20261115/numerical-diagnostic-window.json`.
- Prepared the official native-dense-activations component arm, retaining every
  KDA bound and recording resolved projection selections. The auto-control and
  its failed receipts remain. This arm is not yet GPU-tested or exported; the
  accepted serving core and 4 GiB reserve are unchanged. Local tests: 21 pass.

## 2026-11-15 — First component numerical window failed; B12X restored

- Kit 6b48619 ran on idle SM121 after both nodes passed 114 GiB free/available;
  the isolated qualification extension built without changing the serving CLI.
  Weight/scale checks passed 12/12; all 31 state-transfer cases passed (19 TP2,
  12 TP4). The original expected count 32 was corrected against pinned source
  parameters and collected XML; no case was removed.
- KDA failed unchanged relative-L2 < .01: TP2/width4 .03793176 and TP4/width6
  .02955953. Later prefix-commit assertions were not reached. The four indexer
  cases failed before replay because their old quantized-only fixture could not
  bind NVIDIA mixed-format weights. No numerical pass or adoption is claimed.
- Restored B12X at 21:45:42 UTC, smoke 5/5 at 21:46:30, original images on both
  nodes, watchdog/tailnet active; safety timer disarmed. Raw logs/XML stay private;
  sanitized receipt: `receipts/flare-qualification-20261115/numerical-first-window.json`.
- Prepared a production-factory indexer fixture and post-failure KDA stage
  observations, keeping original assertions and bounds. These follow-ups are
  not yet GPU-tested; 21 local tests pass. Serving reserve remains 4 GiB.

## 2026-11-15 — Matched reference and initial qualification preparation

- Initially registered the inactive qualification unit for 50 cases (actual
  pinned collection later established as 49) with 12 pinned upstream
  checkpoint byte-equality checks. The target CSF cases cover the default A4
  owner; A16 packing/arithmetic remains a distinct open gate. No GPU run yet.
- Replayed the exact first-trial retrieval requests on restored B12X: 13/15
  exact versus Flare 11/15. Both had neighboring-record misses; this small
  stochastic sample does not prove numerical equivalence. Sanitized receipt:
  `receipts/flare-qualification-20261115/retrieval-matched-b12x.json`.
- Started the full three-repetition exact-token B12X reference matrix as bounded
  client unit `b12x-flare-reference-bench.service`; production configuration and
  watchdog remain unchanged. Completed at 21:30:56 UTC: all 84 rows validated, 225 exact cold-prefill
  requests and 90 full-budget decode requests. Candidate comparison remains open.
- Prepared an isolated native qualification unit and a KDA operator test for
  TP2/width4 plus upstream TP4/width6 control, preserving numerical bounds. GPU
  tests were pending at preparation time. The unit includes upstream state-transfer
  cases (count and TP scope corrected above); API smoke now requires sustained-decode cancellation and observed slot
  release. Build/test only after the reference job is terminal and
  both nodes are idle under a new rollback timer.
- Corrected the temperature-zero compatibility description after Exa returned
  conflicting upstream prose: pinned native source clamps numeric zero to .95,
  rather than providing greedy decoding. Added a seventh API smoke case for
  numeric-zero acceptance and malformed-type rejection; live rerun is pending.
- Added a validated last-wins `FLARE_SERVE_RESERVE_GIB` ledger arm for serving
  only. Default and actual candidate reserve remain 4 GiB; a future 3 GiB trial
  is pre-registered in `docs/12-flare-qualification-gate.md`. Twenty-one local
  tests pass. No additional engine or reserve deployment in this follow-up.

## 2026-11-15 — Native Flare trial completed; B12X restored

- Built/exported the pinned NVIDIA checkpoint on both Sparks and served it
  through native Flare, TP2/four slots/MTP-3, loopback 8001. Cold export ~79 min;
  59 graphs/rank. API smoke 6/6; retrieval 11/15 exact, four neighboring-record
  misses, no corruption/error verdicts. Full numerical qualification remains open.
- Native KV planner reports 2,232,064 tokens, about 5% below B12X. One-rep
  exact 8k/16k c1/2/4/8 diagnostic completed; it is not the full matched speed
  matrix. No throughput improvement or production adoption claimed.
- Candidate-only cache isolation fixed permission collisions. Scoped completed
  core cache release recovered physical memory without deleting data or lowering
  the gate. Corrected an expected-shutdown/peer-failure race; 17 local tests pass.
  Lifecycle follow-up staged atomically at kit 747819f; loaded-model stop retest
  remains pending. No host driver/kernel or checkpoint change.
- B12X restored through its unit at 19:53 UTC, health 200 and smoke 5/5; both
  original image identities preserved, watchdog/tailnet active. Candidate ranks
  stopped; safety timer disarmed. Exported core retained for future windows.
- Evidence: `docs/11-flare-trial-20261115.md`,
  `receipts/flare-trial-20261115/`. PR #2 remains draft for unresolved gates.

## 2026-11-15 — Approved retired model weights removed on both Sparks

- User explicitly approved DeepSeek V4/V4.1 variants, MiMo, Inkling and previous
  GLM EXL3 removal after the storage inventory. Deleted 631 weight payload paths
  and 226 snapshot links per node; recipes, tokenizers and metadata remain.
- Recovered **1,986.35 GiB per node (3.88 TiB combined)** in this second wave.
  Free disk: head **2,836.62 GiB**, worker **2,947.48 GiB**. Retired models require
  re-download/reconstruction before reuse. Earlier cleanup receipts are historical.
- Verified the current NVIDIA GLM checkpoint's indexed file sizes/inodes and
  metadata hashes unchanged; named image tags unchanged. B12X service/watchdog
  stayed active, health HTTP 200. No candidate deployment or service restart.
- Root-owned cache files required a constrained, no-GPU cleanup container.
  Its initial 128 MiB limit caused exit 137; resumed the exact manifest with
  512 MiB and verified completion. Receipt: `receipts/retired-models-cleanup-20261115.json`.
- Separate GLM draft models, named images, stopped containers and build trees
  remain. Native Flare dependencies and full integration qualification are pending.

## 2026-11-15 — Authorized housekeeping cleared the disk gate

- Removed unused head Docker build cache, dangling images older than 30 days and
  unreferenced uv cache files. All named image tags were verified unchanged.
- Explicit user authorization then covered retired DeepSeek V4.1 EXL3 shards,
  Engram parts/assembled weights and head source shards on both nodes. Retained
  recipes/metadata; restoring these DeepSeek weights now requires re-download.
- Observed DeepSeek cleanup recovered about 592 GiB per node; free space is now
  about 850 GiB head / 961 GiB worker. Hard-linked file sizes are not additive.
  Receipt: `receipts/flare-housekeeping-20261115.json`.
- Incumbent service/watchdog remain active, health HTTP 200. GLM weights, B12X
  runtime and rollback images are preserved. Disk task removed from shared TODO;
  native dependencies, lifecycle and GPU qualification remain outstanding.

## 2026-11-15 — Flare candidate tooling; deployment prerequisite gate failed

- Added a pinned Flare/FlashInfer recipe, offline command/config renderer and
  read-only per-node readiness inspection in `scripts/flare_candidate.py`.
  Candidate root `/home/nvidia/b12x-flare`, API port 8001; incumbent unchanged.
- Added Flare speculative-counter support to the existing speed smoke, with
  missing/reset/nonfinite counter rejection and zero-draft-round reporting.
  Exact-length/concurrent prefill and native-model qualification remain pending.
- Nine local behavioral tests pass; the vLLM adapter parsed the live incumbent
  scrape. Both-node inventory is in `receipts/flare-preflight-20261115.json`.
- Head disk (~183 GiB free) fails the conservative 250 GiB build/export budget;
  both nodes lack native development prerequisites. Production remains active.
  No candidate installation, build, export, production stop or GPU comparison
  occurred. Unused-build-cache cleanup was proposed; no cache was removed.

## 2026-11-08 — b12x kit deployed; incumbent stopped

- **Deployed:** `/home/nvidia/b12x` serves `nvidia/GLM-5.3-Flash-FP4-Local`
  @ `76348ddb` on vLLM `0.1.dev21830+g8244d1c44` with FlashInfer `0.7.1`
  (`b12x` inside it, commit `91271757`), TP2, MTP-5, 1M context, 17 GiB FP8 KV.
  Image `vllm-node-b12x` = `sha256:3b5da79c…`, identical on both nodes.
- **Cutover:** incumbent `vllm-glm53fp4.service` stopped, watchdog and tailscale
  units disabled; new `vllm-b12x.service` + `vllm-b12x-watchdog.timer` +
  `vllm-b12x-tailscale.service` active and enabled. Boot to `/health` 200 in
  ~5 min; KV pool **2,350,210 tokens** (2.35× at 1M).
- **Reasoning:** requests that omit `reasoning_effort` render
  `Reasoning Effort: Max`; smoke asserts default Max and explicit low/high/max.
- **Gate:** all hard gates passed (hardened receipt `speed-20261108T135615Z`).
  Prefill 2,204–2,309 tok/s; decode c1 27.80, c2 41.74, c4 59.18, c8 58.64
  tok/s; accept length 2.49–2.57, draft accept rate 0.30–0.31 (baseline:
  27.32 / 41.10 / 61.35 / 58.79; 2.29–2.58; 0.26–0.32).
- **Receipts:** `receipts/deploy-20261108T134520Z.txt`,
  `receipts/qualification-20261108T134503Z.txt`,
  `receipts/speed-20261108T135615Z.{json,md}` (after),
  `receipts/speed-20261108T133210Z.{json,md}` (baseline).
- **Rollback:** `/home/nvidia/glm53-fp4-local` + `vllm-glm53fp4.service`
  (disabled, image and `.env` intact). Swap back = stop b12x, start old unit.
- **Memory after boot:** MemFree ~3 GiB / available ~2 GiB per node — same
  posture as the incumbent; no co-located builds while serving.

## 2026-11-08 10:11 — promoted to production; boot auto-start verified

- `vllm-b12x.service`, `vllm-b12x-watchdog.timer`, `vllm-b12x-tailscale.service`
  are enabled, linger is on, and the incumbent units are disabled.
- **Boot proof (receipt `receipts/boot-20261108-second.txt`):** both nodes
  rebooted; the head's unit started by itself at boot (10:05:01), dispatched
  worker then head (10:05:18/19), and `/health` returned 200 at uptime 403 s
  with `vllm_node` up on both nodes at the pinned digest. Tailnet endpoint 200;
  watchdog timer re-armed.
- **First boot failed and was fixed:** the new worker checkpoint check fed a
  heredoc through `ssh`, never executed it, and treated the fallback `1` as a
  missing shard, so `preflight` refused to start (the watchdog reset-failed and
  retried three times). The check is now `scripts/check_checkpoint.py`, fed to
  the worker over stdin; the failure is recorded in `spec/TODO.md` history.

## 2026-11-08 — MTP-3 adopted on the b12x kit

- Window 1 from `spec/TODO.md`. Independent variable: `num_speculative_tokens`
  5 → 3. Matched control re-run on the deployed image (the Nov 3 trial used a
  different build), 3 reps × c1/2/4/8, fixed code prompt.
- Result: c1 37.08 → 40.21 (+8.46 %), c2 +9.18 %, c4 +8.00 %, c8 +8.34 %;
  accept rate 0.47 → 0.63. Prefill 2,230–2,312 tok/s (no regression), KV pool
  unchanged at 2,350,210, smoke 5/5, content and tool calls identical at T=0.
- Watchdog disarmed for the window and re-armed; unit active, `/health` 200.
  Gate: `docs/gates/2026-11-08-mtp3.md`; receipts `receipts/decode-mtp*`,
  `receipts/parity-mtp*`, `receipts/speed-20261108T194204Z.*`.

## 2026-11-08 19:57 — MTP-3 promoted to production; boot path verified

- Production unit restarted from a real two-node power cycle: `vllm-b12x.service`
  (enabled, linger on) started by itself at 19:51:34, dispatched worker then
  head, and reached `/health` 200 at uptime 383 s.
- The recipe is rendered from `/home/nvidia/b12x/recipes/glm-5.3-flash-fp4-local.yaml`
  on every start; both ranks' argv and the resolved `SpeculativeConfig` report
  `num_spec_tokens=3`. KV pool 2,350,210; watchdog timer re-armed.
- Receipt: `receipts/prod-boot-20261109T005748Z.txt`.
