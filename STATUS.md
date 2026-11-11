# Status

## 2026-11-10 — reviewed post-warmup cache trial running

- Final review cleared7fdd343;31 CPU/34 isolated lifecycle checks passed. Both
  actual GPU probes preserved pointers and passed6 graph replays/node after
  cache return, no checkpoint/server. All disposable probe containers removed.
-35 runtime hashes, images/base-loader sources, worker staging, env snapshot
  and memory gates passed. Started `b12x-recipe-window@warmup-cache-return.service`,
  initialPID392726, both actual profiles verified02:24:14Z. Only one new treatment:
  unused CUDA cache return after original warmup; postload cap/17G KV frozen.
  Functional/full matrix pending; all exits stop-only, no adoption/TODO3 verdict.

## 2026-11-10 — postload stabilized; later startup floor failed, models stopped

- Actual target+MTP native0.80 scopes and restoration1.0 verified on both ranks;
 1817 ordered records/rank. Postload minima10.132/11.092GiB; reserved<=97.328GiB.
- After graph capture/engine warmup, head hit1.968GiB at01:58:37Z. Guard stopped
  before health/smoke/speed. Stop-only cleanup01:58:43Z, primary1/recovery0;
  both model objects absent, canonical ledger restored, proxy/watchdog inactive.
- No adoption/TODO3 result. Investigate later startup footprint before retry;
  pinned image already has startup glibc trims and pre-KV CUDA cleanup. Avoid
  duplicate cleanup patches without phase evidence. Receipts
  `receipts/startup-bound-retry/outcome.md`.

## 2026-11-10 — reviewed bound retry running after real-CUDA checks

- Final review cleared9a01728; both GB10/PyTorch2.13 probes passed4/4 actual
  indexed/unindexed cap/restore normal/exception paths without loading weights.
  Disposable probe containers removed.26 CPU/32 lifecycle checks retained.
-30 runtime hashes, both images/base-loader hashes, worker staged bytes, env
  snapshot and memory gates passed. Started `b12x-recipe-window@startup-bound-retry.service`,
  initialPID362204. Keep this handle/output; prior failed attempt preserved.
  Same quant/17G KV/Humming MTP3/four seats. All exits stop-only; no adoption.

## 2026-11-10 — bound setup failed; safe stopped state verified

- First bound attempt raised before activation: fraction API rejected unindexed
  `cuda`. No postload/health/smoke/speed; this does not evaluate the cap.
- Stop-only cleanup completed01:48:13Z (primary143/recovery0), both model objects
  absent, canonical ledger restored, proxy/watchdog inactive. No unsafe reboot.
- Device-index fix atcd83f40 plus fresh retry/real-CUDA microcheck at9a01728 are
  in final review.26 CPU/32 lifecycle tests passed; no retry staged/deployed yet.
  Preserve terminal `local/ab-startup-bound/`; TODO3 remains open.

## 2026-11-10 — reviewed startup-bound trial running

- Code32db0ae cleared final Astra review;26 CPU/32 isolated Linux lifecycle
  checks and actual pinned frontend dry-run passed.29 runtime hashes, both base
  image/loader identities, ordered mods and worker staged bytes verified.
- Started `b12x-recipe-window@startup-bound.service`, initialPID306965.
  Existing memory gates passed head117GiB/worker115GiB free. Same quant/17G KV/
  Humming MTP3/four seats. Native fraction0.80 only during postload; original1.0
  must be proven restored before smoke/matrix. All exits stop both ranks and
  restore canonical ledger without unsafe reboot; no adoption/candidate3 yet.

## 2026-11-10 — guarded startup/recovery failed; both ranks stopped

- Diagnostic proved both installed hashes and1817 ordered target-postload
  records/rank. Layer6 CSF postprocessing left25.24GB reserved-minus-allocated;
  worker briefly1.915GiB before the existing helper released it. Operator stopped
  before health/smoke/speed; external sampling missed the short dip.
- Canonical recovery breached2GiB at01:24:32Z (head1.561GiB) and failed closed.
  At01:24:38Z both containers absent; serving stopped/failed, watchdog and proxy
  inactive. Memory recovered. No automatic retry; no optimization adopted.
- Candidate3 remains open. Evaluate a separate startup-only allocator bound
  before another boot, with Exa/source proof and final review. Existing helper
  works after conversion; a duplicate post-module cleanup is not a proven fix.
  Receipts `receipts/startup-memory/outcome.md`.

## 2026-11-10 — reviewed startup observation started

- Passive loader trace and guarded canonical recovery frozen at4d4d66a; actual
  serving script unchanged.20 CPU tests and24 isolated Linux lifecycle scenarios
  passed, including stale/future heartbeats, blocked-operation observer loss,
  shutdown abort race, terminal retry prevention and A-only observation.
- Final review cleared one diagnostic A-only window after recovery and stdin
  fixes. All25 staged hashes, both images/original loaders, rollback snapshot and
  independent recovery verified before starting `b12x-recipe-window@startup-memory.service`.
  The window isolates healers/proxy; no candidate3 or adoption clearance.

## 2026-11-10 — candidate 3 control aborted; original service healthy

- Fresh Humming A hit0.746GiB host available seven seconds after target weight
  load; guard stopped it before health. B never ran; candidate3 stays open.
- Recovery validated at2026-11-11T00:42:32Z: pinned/default control profiles,
  smoke5/5, health200, serving/watchdog/proxy active. Additional recovery observer
  stopped after validation. No backend, quantization or KV optimization adopted.
- Installed image already has per-module UMA pressure release. Investigate its
  conditions and post-load allocator phases before selecting a repair; do not
  add a duplicate hook blindly. Receipts `receipts/ab-draft-b12x/attempt-outcome.md`.

## 2026-11-10 — candidate 3 paired recipe window running

- Staged reviewed code `af8b87e` into `/home/nvidia/b12x` as nvidia, including
  one-field draft-b12x recipe, profile/kernel evidence checks and independent
  recovery unit. 14 CPU/12 isolated lifecycle tests passed; real frontend A/B
  scripts differ only by draft backend,16 runtime hashes/images verified.
- Started `b12x-recipe-window@draft-b12x.service`; fresh Humming control first,
  then b12x candidate only after its complete matrix. Same image/quant/17G KV/
  MTP3/four seats; watchdog/proxy isolated. Output `local/ab-draft-b12x/`.
  Results and validated restoration pending; no adoption. Both nodes remain on
  kernel6.17.0-1031-nvidia/driver580.173.02.

## 2026-11-10 — allocator candidate rejected; healthy control restored

- Allocator-only 17G trial hit the pre-registered 2 GiB available-memory floor
  on the worker (1.958 GiB); stopped before activation verification/speed smoke.
  No larger KV trial and no optimization adopted. Full control matrix retained.
- Recovery verified 2026-11-11T00:02:40Z: default allocator on both ranks, pinned
  image, 17G FP8 KV/pool 2,350,210, MTP-3/four seats, smoke 5/5 and health200;
  serving unit/watchdog/proxy individually active. Temporary ENV_FILE override
  removed; normal append-only ledger works through the reviewed projection fix.
- Receipts `receipts/ab-20261110/outcome.md`; 10 CPU and 11 isolated systemd
  scenarios passed. Next: candidate 3, with final review before deployment.

## 2026-11-10 — ordered optimization windows in progress

- First allocator-B dispatch failed before model launch: pinned upstream rejects
  duplicate env keys, including appended rollback lines; recovery hit the same
  parser and start limit. Restoring the hash-verified original env through a
  temporary runtime `ENV_FILE` unit override. No allocator speed result exists.
- Fix at `90c92da`: atomic private last-wins projection for upstream while
  retaining `.env` history; normalize failed Docker-inspect output so absent
  ranks confirm teardown. Two regression tests pass; pinned validator accepts
  derived B/rollback configs and rejects original duplicate ledgers as expected.
  Review cleared the retry subject to frontend/override/hash preflight checks.

- Runtime `/home/nvidia/b12x`: saved rollback env/recipe/launcher and image
  identity, stopped both ranks through the unit, restarted the unchanged
  17 GiB/MTP-3 control. Watchdog and external proxy stopped for measurement;
  separate memory guard stops the unit below 2 GiB host available on either rank.
- Added an optional allocator env passthrough, exact-token c1/2/4/8 prefill
  matrix, matched-receipt validation and a dependency-free uv project. Control
  smoke 5/5; full A/B and candidate decisions are pending. Gate:
  `docs/gates/2026-11-10-allocator.md`; runtime receipts `local/ab-20261110/`.

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
