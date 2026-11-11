# Candidate 3 experiment clearance

Final Astra review cleared critical code `af8b87e` conditionally for the
experiment, not adoption. No blocking defect remained after requiring resolved
NVFP4 backend evidence from both rank boot logs before any measurement.

Conditions completed before startup: all12 isolated lifecycle scenarios passed
against final source;14 CPU tests passed; actual pinned frontend dry-runs differ
only in speculative `moe_backend`; all16 runtime files match committed hashes;
both running/local image IDs match the pinned control. Fresh measurement output
had no profiles, memory samples or completion/recovery markers before startup.
Unit template verified `KillMode=mixed` and independent `ExecStopPost` recovery.

The lifecycle fixtures mock every cluster/benchmark operation and shorten
polling to0.1s; they prove recovery behavior, not real kernel selection. The
live window separately requires actual `/proc` profiles and resolved kernel
messages on both ranks. The reviewer independently ran four recipe-validation
tests, syntax and whitespace checks; no deployment or mutation was delegated.

Started `b12x-recipe-window@draft-b12x.service` after all preflights. Fresh A
started 2026-11-11T00:33:06Z. Both actual control rank profiles were verified by
00:33:22Z. Full functional, speed, B and recovery results remain pending.
