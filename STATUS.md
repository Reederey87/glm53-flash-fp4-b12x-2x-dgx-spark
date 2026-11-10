# Status

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
