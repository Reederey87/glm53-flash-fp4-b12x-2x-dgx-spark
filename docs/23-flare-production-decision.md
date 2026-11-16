# Production decision package — qualification in progress

The requested final state is the best qualified Flare candidate serving the
cluster, verified startup/watchdog/reboot recovery, and the completed integration
merged into main and pushed to GitHub. Production adoption is already authorized
after qualification. This document records readiness; it does not declare the
current trial production-ready or waive any existing gate.

## Exact candidate under evaluation

- Native manifest: `406f7d0387b39d6e2c0945c297f82e771df7fba792725f38a46503c34f930a63`.
- Native executable: `6686043d88badbdbb2d152d3d6174a3ca1405fddcc2e6dc34097a3d8667d50c4`.
- Flare source: `5a4e867954593b2e05bba43bc2a6eeaddca402d7` with separately recorded
  prefill-order and bounded-observer patches; dependency locks unchanged.
- Native-activation core: `df2146963651ee93076cf3f579fe4f8d9e19ad0f535929b0132c299fbe01a8ee`.
- NVIDIA checkpoint: `76348ddb2be2e35e39ecfc00e75dc07703f4f3d5`.
- TP2,4slots,MTP3,chunk4096,CP-off,reserve4. Compare balanced versus latency;
  disable tracing for serving performance. Preserve omitted reasoning effort=Max.

## Evidence required for the decision

| Requirement | Current evidence | Remaining decision evidence |
| --- | --- | --- |
| API and model identity | Balanced7/7 API checks; exact core/binary on both ranks | Same checks on selected final arm and production endpoint |
| Prompt latency and decode speed | Balanced native trace confirms interleaving; complete balanced mixed control75 requests/9 cases | Latency trace and matched mixed/full speed gates; retain every failed or inconclusive point |
| Numerical correctness | Native activation component49/49; full scale population audit19,025,362,944 values | Full-model arithmetic, A16/A4, sparse-selection and speculative-state qualification |
| Context and capacity | Candidate2,295,552 KV tokens versus incumbent2,350,210 | Resolve2.33% capacity shortfall and verify long-context admission/retrieval |
| Memory | Completed controls passed sampled bounds | Selected arm passes full workload and lifecycle recovery bounds |
| Shutdown and peer loss | Actual idle native exits0/no forced kill; corrected coordinated-peer checker | Loaded graceful shutdown and injected peer failure with invocation-bound evidence |
| Production ownership | Isolated runtime and tested B12X restoration | One cluster startup owner, bounded watchdog, compatible endpoint and disabled conflicting startup |
| Reboot | Existing trial fallback is transient | Persistent fallback, new boot IDs, both ranks, generation and watchdog recovery |
| Git delivery | Draft PR2 carries committed source and receipts | Resolve applicable checks/review; merge into main and synchronize/push main after production verification |

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
