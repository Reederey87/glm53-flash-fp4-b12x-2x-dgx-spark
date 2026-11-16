# Long-output window registration

Execute docs/31's matched three-repetition workload in
`long-output-window-20261116T080000Z` only after docs/38's corrected six-case MLA observation gate
passes and its B12X restoration and fallback closure are independently verified.
This is an independent required workload, not advancement to the full matrix
or evidence that the unresolved mixed gate passed.

Freeze artifact127424e9/binaryb2eb310b, coredf214696, wrapper41b65a5a,
reserve4, TP2, four slots, MTP3, chunk4096 and CP-off. Both policies trace off.
Local fractional-reserve support is not staged. The head-only long-output client
and its imports have a separate SHA manifest; the worker only needs the frozen
wrapper and identity verifier. Verify all before stopping B12X.

Setup snapshots both runtime ledgers and identities and arms
`b12x-flare-long-output-restore-20261116T080000Z.timer` for60minutes. It stops
`b12x-flare-long-output-orchestrate-20261116T080000Z.service` and both policy
memory monitors before B12X restoration. Orchestration limit50minutes; existing
idle/serving memory gates stay unchanged. Do not start with active B12X requests.

Fresh balanced then latency starts must verify actual executables, core, argv,
trace-off and seven API checks. Record actual pool geometry without representing
it as a capacity pass. Each runs the same12 cold requests and256-token output
budgets under run ID `long-output-20261116`. Require complete output and actual
native exit0/no forced kill on both ranks after each arm. The strict comparator
retains17 comparison points and the existing2%/overlapping-range classification.
Comparator success only establishes complete comparable receipts; it does not
mean every point passed. Restore after both arms or any error. No automatic
adoption or full matrix follows this window. Independent original-image checks,
fresh5/5 B12X smoke, API/watchdog/tailnet and absence of native PIDs are required
before disarming fallback.

Exact helpers are `qualification/windows/long-output-20261116/`. Research,
stronger alternatives and local-source evaluation are in docs/31 and36. No new
engine/kernel/precision setting is introduced by this measurement.
