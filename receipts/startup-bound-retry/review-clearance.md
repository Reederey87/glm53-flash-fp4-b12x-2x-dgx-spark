# Fresh retry clearance

Final Astra review cleared9a01728 (cumulativecd83f40 device-index fix) for the
tiny compatibility check on both nodes, then ONE fresh retry if it passed.
No code blockers remained.26 CPU tests and unchanged32-scenario lifecycle
coverage apply. Retry controls are byte-identical to the first bound config;
only task/output naming and the corrected helper/preflight differ.

Reviewed helper SHA256:
7060fce991761fda22a469d31c790a75d33c124dd3576f6464a65876aba1e6df.
Both actual pinned PyTorch2.13/GB10 probes passed indexed/unindexed normal and
exceptional paths,4/4 per node. Each used four1MiB allocations/deletions, restored
fraction1.0, loaded no server/checkpoint, ran with PYTHONOPTIMIZE=0/no-O flags,
and removed its disposable container. Raw stdout/stderr receipts are retained.

Before the checkpoint restart:30runtime hashes, both unchanged images/original
loader hashes, worker staged mods/probe, canonical env backup, fresh output,
mixed-mode independent ExecStopPost and two-node memory gates passed. Started
`b12x-recipe-window@startup-bound-retry.service`, initialPID362204.

The trial retains0.80 postload cap,4GiB trace headroom,2GiB host guard and
healthy-only smoke/parity/full matrix. Every exit is stop-only. No adoption,
unsafe-control restart or draft-backend test is cleared; their decisions remain
separate. No cluster action or source edit was delegated to the reviewer.
