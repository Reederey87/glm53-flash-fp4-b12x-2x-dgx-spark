# Remaining expert arithmetic gate

This registers the remaining A16/A4 component check without changing the native
binary, accepted core, checkpoint, source pins or numerical bounds. It does not
complete the separate full-model and state/capacity gates.

Exa reviewed the primary [FlashInfer CSF tests](https://github.com/flashinfer-ai/flashinfer/blob/1bdba872/tests/utils/test_csf_scales.py),
[CSF representation](https://github.com/flashinfer-ai/flashinfer/blob/1bdba872/flashinfer/quantization/csf.py)
and [Flare qualification backlog](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/TODO.txt).
The direct pinned-file fetch timed out; the clean local FlashInfer tree at
4fd836dcda0998b875129aad76774ca073df10c8 supplies the exact installed revision.
Current web results do not replace this source pin. Reviewed its precision/replay
tests, local vLLM's expert activation/calibration handling, TensorFold's explicit
checkpoint A4/A8 arithmetic and exllamav3's shape/dtype-specific recurrent-state
ownership. None is a substitute for hardware results on this recipe. Changing
kernel precision or adopting another engine is a separate candidate.

`qualification/run_expert_numerics.sh` selects 54 unchanged upstream cases:

- Eight declared-precision poisoned-scale replays, 128/4096 tokens, both ID
  dtypes and implicit/explicit declarations. A16 inline/expanded equality at 128;
  at 4096, original max-absolute 0.0625 and RMSE 1.1e-4; A4 relative error <0.004.
- Twenty-one A4 float64-emulation cases, retaining calibrated scales, SwiGLU
  variants and original relative error <0.004.
- Twenty-four native expert compressed/plain comparisons with poisoned shared
  scratch, A4/A16, live counts 1/17/33 and four intermediate widths.
- One planned A16 scale-expansion replay across live counts.

Require every selected case to execute and pass, with zero skips and exact count.
Retain failures, source hashes, environment, test exit and XML. Synthetic
component agreement plus the full checkpoint-scale audit does not establish
full-model output equivalence. The two-local-GPU launcher-ownership test is not
selected because each Spark has one GPU; it is not described as passed.

The test-only archive is produced by `git archive` from the exact FlashInfer pin
for tests/experimental/b12x and its package init files. Its SHA256 is
`af1c134345ab093c5912b699bce7a246d0b988267ef5958b1ded89b53e4c7414`.
Extract into a new immutable qualification directory and record/check every file
hash before execution. Use the existing Flare venv through uv, with no sync or
dependency installation. The script verifies the installed dependency's direct
URL revision and actual SM121 GPU before running. It never changes the serving
extension or accepted core.

Execution must wait until the active performance window closes. A separate
60-minute B12X restoration timer, snapshots, idle containers/ranks, 90 GiB free
and 100 GiB available on both nodes precede the test unit. The test timeout is 40
minutes. The fallback must stop the exact qualification unit before restoration.
Afterward require original B12X images, fresh 5/5 smoke, health, watchdog/tailnet
and no native processes before disarming. Record concrete unit names and time
before starting. This registration alone is not a test result.

Concrete window: `expert-numerics-window-20261116T053000Z`. Setup refuses until
the bounded-retry window has independent B12X restoration and timer-disarm
receipts. The exact window and memory units use the
`b12x-flare-expert-numerics-{window,memory}-20261116T053000Z` prefix; the
60-minute restoration helper stops both before restoring B12X. The client unit
has a 50-minute runtime limit. Head-only tests leave the worker idle; the
two-node memory monitor remains enforcing. Snapshot both runtime ledgers,
supervisor/core acceptance hashes and rollback images, and require them unchanged
after testing. Helpers are in `qualification/windows/expert-numerics-20261116/`.

## Hardware result

All 54 cases passed on GB10/SM121 with the installed4fd836dc dependency in
166.71 seconds; no skips and no tolerance changes. Retained pytest exit0, XML,
environment/source records and both-node memory observations. All before/after
runtime supervisor, ledger and accepted-core hashes matched. This closes the
selected component arithmetic/replay gate, not full-model equivalence.
Restoration was queued automatically; independent B12X smoke/closure follows.
Receipts: `expert-numerics-*` in `receipts/flare-qualification-20261115/`.

Window closed05:32:52 UTC after independent fresh5/5 B12X smoke, original images
on both nodes, active API/watchdog/tailnet and no native processes. Restoration
and fallback-disarm receipts are retained alongside the numerical results.
