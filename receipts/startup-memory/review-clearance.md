# Diagnostic startup observation clearance

Final Astra code review cleared `4d4d66a` (including280f1ef) for ONE diagnostic
A-only window, not candidate3 or adoption. Initial reviews found cleanup,
observer-supervision/handoff, comparison-wording and stdin defects; all were
fixed before staging. No production calls or mutations were delegated.

20 CPU checks, pinned-source transform/hash/executable-AST checks and shell
syntax passed. The fresh24-scenario Linux lifecycle rerun completed against
final source, with cluster/API calls mocked and profile stdin actually consumed.
It covers observer loss while blocked in startup/smoke, stale/future heartbeat,
shutdown abort/terminal status, interruption, terminal retry prevention and a
successful observation-only arm. A separate real idle transient-unit probe
confirmed its terminal properties remain queryable after collection.

Remaining startup conditions: staged25-file hashes, pinned both-rank images and
original loader hashes; supported pre-serve mod hook; rollback snapshots, fresh
output, independent ExecStopPost, healer/proxy isolation and two-node memory gate.
Require both trace installation hashes/ordered module boundaries, health before
functional/full matrix, unchanged2GiB floor and terminal recovery safety failure.
Restoration must prove canonical untraced loader hashes, smoke/health and
observer reconciliation before access returns. See gate for all frozen controls.
