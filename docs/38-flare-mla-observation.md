# MLA observation defect and registered retry

> Historical architecture or qualification record. Current production, unresolved gates and the research pause: [docs/63](63-production-pause-checkpoint.md). Old window controllers must be adapted before reuse.

The first docs/34 hardware run failed all six cases in63.22s, pytest exit1,
with no skips. Only the `attended` stage was reported mismatched: maxima
0.6875–1.75 across the cases. Every other checked stage, including expanded
values and final output, passed the original exact comparisons; persistent
state, sparse-selection assertions and allocation checks reached completion.
This is a failed gate, not qualification. Automatic B12X restoration started.
XML, environment, source identities and actual failure messages are retained as
`native-mla-initial-*`; no tolerance is relaxed.

## Source diagnosis

Pinned `MLAScratch.allocate` initializes `attended` to zeros.
`PreparedGlmMLA.forward` obtains the real attention tensor as a local variable,
uses it for value expansion and final output, but never binds it into the
returned scratch record for the non-CP path. The upstream test copies that
zero placeholder into its observed stage, then compares it to a freshly computed
real attention tensor. This is a source-visible observation defect; it does not
establish that all attention arithmetic is correct.

Exa lookup for the exact forward return did not identify an upstream fix.
Reviewed the primary [GLM scratch/export defect report](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/glm-batched-speculation-defect.md)
and [prepared model contract](https://github.com/NVIDIA/flare-local-inference/blob/main/helios/model-contract.md),
then pinned Flare's functional attention output ownership, vLLM MLA output
handling, exllamav3 scratch ownership and TensorFold's cloned diagnostic/state
snapshots. Unlike the export defect, this failure's source is the diagnostic
return: downstream outputs already compare exactly. Do not port an unrelated
indexer change or claim a serving-engine fix.

## Qualification-only correction and unchanged gate

`qualification/mla_observation.py` copies the pinned forward method and adds
one non-CP binding: `s = replace(s, attended=attended)`. It exposes the already
computed tensor to the existing test's copy. It does not add a new attention
call, change a kernel, overwrite expected values or remove a comparison.
The fixture compares the entire method AST with the pinned original after
removing this one binding and normalizing the function name; any other drift
fails. The original test file SHA remains checked. The method replacement is
process-local to qualification and is never staged as serving source or exported
into a core. The original wrapper/control remains in Git and failed receipts.

Retry in `mla-observation-window-20261116T073000Z` only after the failed window's
original B12X images, fresh5/5 smoke, API/watchdog/tailnet, no native PIDs and
fallback disarm are independently verified. Reuse all docs/34 controls and
bounds: six exact cases, three replay steps each, zero skips/errors/failures,
pytest exit0; no relaxed numerical or selector allowance. Retain the same
checkpoint, FlashInfer, extension, TP2 shard, native dense activations and seed.
No serving code, core, wrapper, reserve, driver or kernel change.

Setup snapshots both nodes and arms the exact
`b12x-flare-mla-observation-restore-20261116T073000Z` timer for60minutes before
B12X stop. Runner unit `b12x-flare-mla-observation-window-20261116T073000Z`
has50minutes; pytest40minutes. Existing idle and serving memory gates remain.
Fallback stops the exact runner/monitor before restoring. Independently verify
B12X before disarming. Only all six passing corrected observations close this
component gate; full-model equivalence remains unproven.

Initial failed window restoration verified05:57:20 UTC with fresh5/5 smoke,
original images, active API/watchdog/tailnet and no native PIDs; fallback disarmed.
Corrected observation retry started after source SHA checks and its own timer.

Corrected hardware result: all6 cases passed in30.59s, pytest exit0, no skips
or relaxed bounds. All7 two-node memory samples passed; both ledgers, accepted
core and supervisor hashes unchanged. The original failing control stays retained.
B12X restoration is running; fallback remains armed until independent closure.

Restoration independently verified06:04:45 UTC: original images, fresh5/5 smoke,
API/watchdog/tailnet and absent native PIDs; fallback disarmed06:04:46 UTC.
