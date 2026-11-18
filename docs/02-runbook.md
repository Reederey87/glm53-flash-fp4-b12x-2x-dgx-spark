# Production runbook — Flare

Current release and operational receipts: [docs/63](63-production-pause-checkpoint.md).
Research is paused. The release is explicitly approved provisional production,
not a completed performance or broader quality qualification.

## Startup, shutdown and health

Run as `nvidia` on spark1, from the runtime `/home/nvidia/b12x-flare`:

```bash
systemctl --user status b12x-flare-production.service
systemctl --user is-active b12x-flare-production-watchdog.timer b12x-flare-tailscale.service
curl --fail http://127.0.0.1:8001/health
systemctl --user stop b12x-flare-production.service
systemctl --user start b12x-flare-production.service b12x-flare-tailscale.service
```

The head owner explicitly starts the worker across `192.168.177.11` before
starting the head supervisor. Both user managers
have linger. The owner verifies the hashed approval and per-rank recipe/core pins,
the native artifact, idle memory, both ranks, API health, consistent cache geometry
and the provisional 2,300,000-token minimum, then all seven API smoke checks.
Startup receipts are `local/production-smoke-<owner-invocation>.json`.
The original 2,350,210-token qualification target remains open.

`Type=exec` on a rank means its supervisor started, not that the model is ready.
The owner dispatches a fresh worker invocation before readiness, so a retained
failure from a previous invocation is not mistaken for a new startup failure.
Readiness is bounded by 900seconds; failed ranks and ranks disappearing after
start fail promptly.
Read the owner journal first, then `logs/serve-rank0.log` and the worker log.

The existing tailnet port 8000 forwards to native loopback 8001. The API has no
application authentication; Tailscale remains the access boundary. A manual
stop respects operator intent. Starting the owner after a manual stop also
requires starting the proxy, as shown above.

## Watchdog and maintenance

The timer checks every 30seconds, requires two failed observations, and may
restart an active owner at most three times per six hours. Attempts survive
reboot in `local/production-watchdog/state.json`. It never resurrects a manually
stopped, disabled, failed or currently starting owner.

A **failed startup** is recovered by the unit itself, not by the watchdog. When a
start fails only because the observed cache pool is below the approved gate,
`flare_production.py` records the attempt and exits 75, and `Restart=on-failure`
retries after 60 seconds. Two retries per six hours are persisted in
`local/production-startup-retry/state.json`; the next failure exits 78, which
`RestartPreventExitStatus=78` makes terminal, so the owner stays failed for
operator diagnosis or the pre-armed rollback. Every other startup failure also
exits 78 and is never retried: a restart may only ever be authorised by the
persisted retry budget. Do not clear either budget to loop.

For planned work, create `local/production-maintenance`, stop the watchdog timer,
and stop the owner. Remove that marker before an intentional owner start and
restart the timer after health/smoke. Atomically stage scripts and append `.env`
changes; never overwrite a script while it is executing. Preserve snapshots,
exact fingerprints and a verified rollback for every future window.

## Controlled rollback to B12X

Keep the original B12X image `sha256:3b5da79c42ed4204440cfb07c6de1eba46441d5cba6b57d5428d44e60c10d0ed`
on both nodes and `/home/nvidia/b12x` intact. For an intentional rollback:

```bash
systemctl --user disable --now b12x-flare-production-watchdog.timer b12x-flare-tailscale.service
systemctl --user disable b12x-flare-production.service
systemctl --user stop b12x-flare-production.service
systemctl --user enable vllm-b12x.service vllm-b12x-watchdog.timer vllm-b12x-tailscale.service
/bin/bash /home/nvidia/b12x-flare/scripts/flare_restore.sh
systemctl --user start vllm-b12x-watchdog.timer vllm-b12x-tailscale.service
/home/nvidia/.local/bin/uv run --offline --no-project --python /usr/bin/python3 /home/nvidia/b12x/scripts/smoke.py --base http://127.0.0.1:8000
```

Verify original image IDs on both nodes and fresh 5/5 before declaring rollback
complete. The disk-persistent adoption fallback uses a pending marker and UTC
deadline; it is disarmed after successful operational verification. Its helper
is intentionally a no-op without that marker. Do not assume an old experiment's
transient restore timer changes production ownership correctly.
The [historical B12X runbook](64-b12x-rollback-runbook.md) describes that engine.

## Resume research

Read docs/63 and the ignored canonical `spec/TODO.md`. Rebase old controllers
onto the current Flare owner, register a new gate and rollback, and perform Exa
MCP lookup plus local source review before critical changes. Do not run the
staged warmup or capacity windows blindly. Do not change host driver/kernel.
