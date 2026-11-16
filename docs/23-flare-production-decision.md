# Production decision — explicitly approved provisional release

On 2026-11-16 the user explicitly adopted the current Flare candidate after its
seven API checks and paused further research. This supersedes the earlier
pre-adoption research gate. It does not waive or pass the unresolved numerical,
capacity, quality and performance qualification. The exact hashed decision is
`recipes/flare-production-decision-20261116.json`; current operational evidence
and the resume checkpoint are in [docs/63](63-production-pause-checkpoint.md).

The matrix below records the earlier qualification checkpoint. MTP replay has
since passed (docs/62), generation remains partial (docs/53), and warmup remains
unrun (docs/61). The release is approved-provisional, not fully qualified.

## Selected candidate — research paused

- Native manifest: `127424e92c1e5845697d85f3c34ce93fa632dd48bf3be491c868c50a9deb0243`.
- Native executable: `b2eb310b9ec9009fa499086777d9ed90105b323db70da527242286dc0de026b9`.
- Flare base: `5a4e867954593b2e05bba43bc2a6eeaddca402d7`; bounded scheduler source
  frozen at `0c8f805fae82b768591fc908a936a7efec672234` in this kit.
- Native-activation core: `df2146963651ee93076cf3f579fe4f8d9e19ad0f535929b0132c299fbe01a8ee`.
- NVIDIA checkpoint: `76348ddb2be2e35e39ecfc00e75dc07703f4f3d5`.
- Supervisor SHA: `41b65a5a4bc39af18de9310d4096752809c223bea7ca4994cf8c2aa6f97e8793`.
- TP2, four slots, MTP3, chunk4096, CP-off, reserve4, tracing off, reasoning=Max
  when omitted. Fresh balanced versus bounded-latency comparison: docs/29.

The earlier age-policy artifact406f7d03 is rejected by the mixed performance
case. Its equal-long-prompt diagnostic gains do not qualify it for production.

## Evidence required for the decision

| Requirement | Current evidence | Remaining decision evidence |
| --- | --- | --- |
| API and model identity | Seven checks passed on latest balanced startup; exact core/binary on both ranks | Selected final arm and production endpoint |
| Prompt latency and decode | ABBA completed348 requests;70/80 points meet median gate,10 unresolved, no separated regressions (docs/50) | Diagnose unresolved points; full84-row speed gate remains blocked |
| Numerical correctness | Native activation49/49,54 expert,6 MLA,9 layer and2 full-target cases/rank; checkpoint vocabulary reference2/rank; full scale audit19,025,362,944 values | Remaining full-model/reference, MTP and state/retrieval qualification |
| Context and capacity | ABBA observed2,331,392–2,335,232 tokens at reserve4; varies with startup memory | At least2,350,210 plus long-context admission/retrieval and hybrid-state reuse |
| Memory | Enforcing two-node memory monitor active in fresh comparison | Selected arm's complete workload bounds |
| Shutdown and peer loss | Loaded graceful9.75s: both native exits0; injected peer failure3.32s: head exit1; no forced kills; streams closed and locks released | Confirm final selected artifact remains covered; production watchdog recovery |
| Production ownership | Local owner/watchdog/pin/fallback code; seven focused tests and static unit verifier passed | Install/qualify one startup owner, compatible endpoint, disabled conflicting startup |
| Reboot | B12X restoration verified04:53 UTC; trial fallback active during next comparison | Persistent fallback, new boot IDs, both ranks, generation and watchdog recovery |
| Git delivery | Draft PR2 retains source and receipts | Checks/review, merge into main and synchronize/push after production verification |

## Production recovery design under review

Exa's official [timer contract](https://freedesktop.org/software/systemd/man/latest/systemd.timer.html)
states that Persistent applies to calendar timers, so the reboot test needs a
disk-installed absolute OnCalendar fallback with Persistent=true and a pending
qualification marker. The current transient180-minute timers are not that gate.
Only remove the marker/disarm fallback after both-node reboot evidence passes.

The [systemd unit contract](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html)
warns that reset-failed and unit collection clear start-limit counters. The
watchdog therefore needs a retained, bounded restart ledger in addition to unit
rate limits. Preserve manual-stop intent and maintenance windows, test both-rank
health, and wait for teardown and the original two-node idle-memory gate before
restarting. One owner must coordinate both native ranks; competing rank-level
restart loops are unsuitable for the shared collective execution.

[WatchdogSec](https://freedesktop.org/software/systemd/man/latest/systemd.service.html)
requires native sd_notify heartbeats. Do not configure it as though an HTTP probe
supplied those heartbeats. Use an explicit bounded health/recovery timer unless
native notification support is separately implemented and qualified. Verify
user lingering and actual peer readiness at boot; ordering alone is insufficient.

## Rollback and approval boundary

Keep B12X runtime `/home/nvidia/b12x`, original image
`sha256:3b5da79c42ed4204440cfb07c6de1eba46441d5cba6b57d5428d44e60c10d0ed`
on both nodes, and its startup/healer definitions. Restore through
`scripts/flare_restore.sh`, preserving append-only native arm history and the
original memory gates. Before boot adoption, extend recovery to restore startup
ownership and endpoint routing as well as current processes. Never delete this
rollback while qualifying Flare. No host driver/kernel update is part of this work.

Select the best candidate from matched evidence, record exact production bytes,
run final smoke and reboot/recovery gates, then merge PR2. A passing component,
an idle exit or a diagnostic timing does not complete the broader requirements.
