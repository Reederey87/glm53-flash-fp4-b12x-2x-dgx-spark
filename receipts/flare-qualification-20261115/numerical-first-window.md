# First component numerical window — failed

Run: 2026-11-15 21:35:26–21:39:58 UTC on head SM121, kit `6b48619`.
Both nodes were idle with 114 GiB free/available. The 90-minute restoration timer
was armed before B12X stopped. The pinned qualification extension built in an
isolated import path; serving CLI and lock hashes stayed unchanged.

| Check | Observed outcome |
| --- | --- |
| Checkpoint weight/scale preservation | 12 passed; no skips |
| Indexer native replay | 4 fixture failures before replay: quantized-only projection cannot bind `GroupedLinearWeights` |
| KDA TP2, verification width 4 | Relative L2 .0379317626; fails < .01 |
| KDA TP4, verification width 6 | Relative L2 .0295595303; fails < .01 |
| State transfer | 31 passed; no skips; 19 TP2 and 12 TP4 cases |

The original state-test count of 32 was incorrect. Pinned parameter lists and
collected XML contain 9 + 10 + 10 + 2 = 31; no test was removed. The actual suite
contains 49 cases. KDA failed before its subsequent prefix-commit assertions,
so those assertions do not have a passing receipt. The target CSF storage checks
use the A4 owner and do not establish deployed A16 packing or activation math.

B12X was restored at 21:45:42 UTC, then passed all five smoke checks at 21:46:30.
Both nodes retained image `sha256:3b5da79c42ed4204440cfb07c6de1eba46441d5cba6b57d5428d44e60c10d0ed`.
Watchdog and tailnet were active; the safety timer was disarmed after smoke.
No reserve change or Flare adoption occurred.

The worker has no incumbent runtime tree: the head launches its container. Its
candidate `.env` was absent, so it used the recipe default reserve. Snapshots
recorded these absences and actual container/configuration state before shutdown.

`numerical-first-window.json` contains case outcomes, scalar errors and raw XML
hashes. Raw XML/logs, which include tensor dumps, remain private. The next
pre-registered diagnostic window uses production MLA's projection factory in
the indexer fixture and observes KDA intermediate stages after the original
comparison; neither adjustment is a serving-engine fix or a numerical pass.
