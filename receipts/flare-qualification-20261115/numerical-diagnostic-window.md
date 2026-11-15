# Diagnostic numerical window — KDA still fails

Kit `e8b6ac0`, head SM121, 2026-11-15. Both nodes passed the unchanged memory
gate (about 115 GiB free). A new 90-minute timer protected restoration.

The corrected indexer fixture used the same mixed-projection factory as production
MLA and passed all four native replay cases: decode2/decode32 and prefill65/4096,
including poisoned readbacks, inactive rows and allocation counters. All 12
weight checks and all 31 state-transfer cases passed again. Neither result
establishes full-model numerical correctness.

The original KDA graph comparison reproduced both failures exactly. Diagnostics
ran afterward, observing eager intermediate values without changing the bound.

| Stage relative L2 | TP2 / width4 | TP4 / width6 |
| --- | --- | --- |
| Input projection | .02567028 | .02558133 |
| Convolution | .02388527 | .02658763 |
| Forget gate | 0 | .00001575 |
| Beta | 0 | 0 |
| Output gate | 0 | 0 |
| Gated recurrence | .02802200 | .02987997 |
| Output | .03793176 | .02955953 |

All observed values were finite. The first substantial difference occurs before
convolution/recurrence. Projection precision selection is a hypothesis to test,
not a proven cause; stage observations may perturb timing. Original output L2
must still be < .01, and subsequent prefix-commit assertions remain unqualified.

B12X was restored at 21:58:08 UTC, passed smoke5/5 at 21:58:36, retained both
original image identities, and had watchdog/tailnet active before timer disarm.
No source pin, serving core, reserve or production adoption changed.

`numerical-diagnostic-window.json` retains scalar diagnostics, per-case outcomes
and XML hashes. Raw XML/logs remain private. The next registered component arm
uses the official native-dense-activations option and records resolved projection
selections while preserving all original numerical checks.
