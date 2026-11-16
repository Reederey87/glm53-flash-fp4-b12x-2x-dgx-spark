# Changelog

## 2026-11-16 — PR #2: approved Flare release and research checkpoint

- Selected the exact native Flare artifact `127424e9…` / binary `b2eb310b…`
  with core `df214696…`, TP2, four slots, MTP-3, chunk 4096, latency policy,
  reserve 4 GiB and tracing off. The user approved provisional production after
  seven API checks and paused further research.
- Added pinned production startup, bounded persistent watchdog recovery, the
  existing tailnet endpoint and a reboot-persistent adoption rollback. Retained
  the original B12X image and runtime for recovery.
- Fixed initial worker-dispatch readiness and bounded the activation script's
  proxy-listener wait. The first controlled watchdog test exposed retained
  worker failure state; the owner now starts a fresh worker before the head.
  Failed attempts and original-image rollback receipts remain retained. All 100
  local tests pass.
- Retained complete native diagnosis and full MTP 5/5 per-rank replay evidence.
  Preserved the interrupted 100-baseline/86-candidate generation comparison;
  it is incomplete. Warmup and fractional-reserve experiments remain unrun.
- Updated current operations, attribution, historical-document scope and the
  resume checkpoint. Remaining performance, capacity, independent correctness
  and context/state gates are recorded in docs/63 and the ignored spec/TODO.md.

- Verified controlled watchdog recovery and automatic startup after rebooting
  both nodes; post-boot API7/7, exact identities, proxy generation and persisted
  watchdog history pass. Current pool2,347,264 tokens. Host versions unchanged.
- Archived the adoption pending marker and disabled its temporary fallback at
  12:15:45 UTC. Flare startup/watchdog/proxy remain active and enabled.

Detailed startup, watchdog and reboot results are recorded in
[the production checkpoint](docs/63-production-pause-checkpoint.md).
