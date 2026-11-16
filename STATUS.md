# Status

## 2026-11-16 UTC — Additional Exa evidence for latency qualification

- Compared primary aging, cross-GPU scheduling, Sarathi and current vLLM sources.
  Evidence supports a waiting-time hypothesis but does not predict this GPU/model.
- Documented mixed-arrival/decode-gap checks and limits in docs/17; no change to
  the frozen treatment or its numerical/performance acceptance thresholds.

## 2026-11-16 UTC — Prompt-latency candidate passes native CPU coverage

- Added opt-in age-aware prompt completion ordering; at four equal prompts,
  first outputs move from chunks29/30/31/32 to8/16/24/32 in the native selector.
- Worker tests:317 scheduler,2 config,1 CLI passed;2 manual planning benchmarks
  ignored, not passing evidence. Both Cargo locks unchanged; serving untouched.
- Added immutable native-binary selection and append-only policy rollback;
  45 local tests pass. Release build and live latency qualification remain open.

## 2026-11-16 UTC — Production authorization and scheduler fix priority

- User explicitly authorized adoption after qualification, boot/watchdog ownership
  and controlled reboot verification. Recorded the full requirements in TODO.
- Registered a separate worker CPU prerequisite window to fetch locked test
  dependencies after the offline attempt ended; serving artifacts remain frozen.

## 2026-11-16 UTC — Worker scheduler diagnostic stopped before compilation

- The isolated CPU diagnostic failed offline dependency resolution (`rcgen`
  missing), with retained exit101. No test ran and no dependencies were installed.
- Recorded the failure and unchanged preparation source in docs/15 and receipts;
  stopped its exact worker unit, verified MainPID=0. Head scale audit continues.

## 2026-11-16 UTC — Full scale scan active; scheduler diagnostic frozen

- The head is scanning all 42 routed-expert layers under the registered
  70-minute CPU limit after both idle-memory gates. B12X is intentionally stopped;
  automatic restoration is armed for 02:10:40 UTC.
- Added a CPU-only production-selector diagnostic for the two existing scheduler
  presets. It will run in a separate worker test worktree with cached dependencies
  and resource limits; no serving binary or runtime configuration changes.

## 2026-11-16 UTC — Selected-layer CPU scale audit completed

- On the idle head, independently decoded every expert in layers 3, 24 and 44
  for both TP2 partitions: 1,358,954,496 scales, none below the packed A16
  boundary, no CUDA initialization. Runtime hashes remained unchanged.
- Recorded the scope and evidence limits in docs/14. The remaining 39 target
  layers and native packing/replay are still open; a separate all-layer window
  is pre-registered. B12X was restored at 00:38 UTC with original images,
  health200, smoke5/5 and watchdog/tailnet active; the timer is disarmed.

## 2026-11-16 UTC — Full native matrix completed; latency gate failed

- Collected and validated all 84 matched rows per engine, 315 matching request
  hashes, 225 cold prefills and 90 full 200-token decodes. Aggregate decode
  improves 7.4–13.9%; 14/20 per-request prefill points regress beyond the gate.
  Full measurements and the Exa-guided scheduler investigation are in docs/13.
- Serving memory passed 1,035 observations on both nodes. The loaded lifecycle
  client failed before sending a signal because its property count was wrong;
  fixed exact-field validation locally, with 42 tests passing. Hardware rerun
  remains open. Both Flare ranks subsequently stopped cleanly for B12X restoration.
- B12X restoration verified at 00:22 UTC: original image on both nodes, health
  200, smoke 5/5, watchdog and tailnet active. The restoration timer is disarmed;
  candidate ranks remain stopped and no production adoption occurred.

## 2026-11-15 — Reproduction guide aligned with current acceptance guards

- Documented all seven accepted-core fields, the exact export receipt, verified
  native inspection, public-profile handling and atomic transfer to the peer.
  Exa signing documentation confirms local signature trust is not NVIDIA identity.
- Updated the README to the native-activation core and current evidence. No
  runtime or measurement client changed; the full speed matrix remains active.

## 2026-11-15 — Full-layer scale audit prepared for an idle window

- Added a CPU-only audit of every expert in selected target layers, both TP2
  partitions, independent CSF decoding, and the full-layer A16 lifting factor.
  It records scale counts and source hashes; it is not native replay evidence.
- Forty local tests pass. A separate bounded idle window is registered before
  scanning actual checkpoint values. The live serving matrix is unchanged.

## 2026-11-15 — Precision audit narrowed the remaining A16 check

- Updated the audit with the49 passing component cases and verified native core
  metadata limitations. Source review found a conditional packed-scale discard
  boundary whose applicability to the full GLM layers is still unmeasured.
- Exa and local source evidence distinguish this from a demonstrated checkpoint
  failure. No engine or precision setting changed; the live matrix continues.

## 2026-11-15 — Strict matched-matrix comparison prepared

- Added full-matrix validation of request identity, token counts, cold-cache
  observations, timing and per-run speculative rates. Reports preserve all
  repetitions and distinguish separated regressions from noisy median changes.
- Thirty-six local tests pass, including rejection of incomplete/mismatched
  evidence. No running client or engine changed; final comparison waits for
  the native matrix to finish.

## 2026-11-15 — Loaded lifecycle qualification prepared

- Added a guarded candidate-only client for rank-zero shutdown and injected worker
  loss during observed active decode. Each requires terminal rank states, closed
  HTTP streams and released operation locks; the explicit rollback timer remains
  armed. Exa and the pinned local engines informed the pre-registered checks.
- Thirty-two local tests pass. The live speed matrix remains undisturbed; neither
  lifecycle check has run yet. No engine, checkpoint or serving knobs changed.

## 2026-11-15 — Native-activation core exported and serving smoke passed

- Export f6a8f3e completed with both ranks exit0; new core df214696 has verified
  signatures,59 graphs/rank and exact local activation provenance. Primary hash
  `2c47847a8fa28aa375af499973e5d8f8a7259136b0b3347a1fcf7b4fb711d0c6`.
- Native serving is healthy on both nodes; all7 API checks passed. Cancellation
  followed35 generated tokens, recorded one cancellation, drained all slots,
  and subsequent generation passed. Numeric T0 clamping and string rejection
  are verified; default reasoning remains Max. Receipts:
  `receipts/flare-qualification-20261115/native-activation-{export,smoke}.json`.
- At reserve4, loaded86.59GiB/rank, planned cache14.97GiB,2,295,552 tokens and
  178 shared snapshots. Capacity remains2.33% below B12X; no adoption claim.
  B12X is intentionally stopped during the serving trial, whose fallback is
  armed for2026-11-16 01:10:57UTC. The memory monitor is active; speed, retrieval,
  full-model numerical and lifecycle gates remain open. Cold concurrent
  precheck passed4/4 with zero cached tokens; full matched speed matrix started
  at22:46:06UTC in b12x-flare-native-full-bench-20261115T224057Z.service.

## 2026-11-15 — Continuous serving-memory gate prepared

- Added five-second two-node host-memory receipts and optional enforcement of
  the existing 1.5GiB free / 8GiB available serving limits through the pre-armed
  restoration service. Source-qualified through Exa and the local engines.
- Thirty local tests pass. The monitor is not running during export and changes
  no engine or memory settings. Native graph warmup/compilation passed; export
  publication remains in progress under the existing rollback timer.

## 2026-11-15 — Native export running; matched retrieval tooling prepared

- Frozen runtime f6a8f3e is exporting on both Sparks with native activations
  confirmed in its resolved plan. B12X is intentionally stopped; automatic
  restoration is armed for 2026-11-16 00:04:22 UTC. Both memory gates passed.
- Added a pinned-fixture cold/forked retrieval client with observed cache checks,
  per-run speculative deltas, graph shapes and sanitized receipts. All27 local
  tests pass; no live retrieval claim yet. The running export bytes are unchanged.

## 2026-11-15 — Native dense activations pass all component checks

- Frozen kit 6bf1900 passed all 49 SM121 checks: weights12, indexer4, KDA2,
  state31. Both KDA geometries have output relative L2 0.0, and every original
  prefix-state/history/subsequent-decode bound passed. Resolved blockscaled
  input/output projections use quantized mode; BF16 partitions remain BF16.
- B12X restored at 22:09:00 UTC; smoke5/5 and both original images verified at
  22:10:03, watchdog/tailnet active, restoration timer disarmed. Candidate stopped.
  Receipt: `receipts/flare-qualification-20261115/numerical-native-activation-window.json`.
- Added the supported export option and local provenance checks binding the
  successful resolved plan to a newly published primary hash. The old accepted
  core cannot satisfy the new guard. This supplements the upstream signed
  manifest, which omits this option; it is not a signed precision attestation.
  A separate export/serving trial remains unrun; reserve stays 4 GiB.

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
