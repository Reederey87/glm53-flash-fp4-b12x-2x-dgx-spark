# Mixed-workload diagnosis after rejected latency policy

The completed untraced mixed comparison in docs/22 rejects the age-aware policy.
Keep the failure and original gate; do not proceed to adoption on equal-length
prompt timings alone. B12X restoration was verified before this diagnostic.

## Exa and pinned source review

Exa retrieved [Quota-Based Aging](https://arxiv.org/pdf/2610.17795): unrestricted
aging can over-promote old long requests. Its quota/debt mechanism bounds
promotion, and counts completed short admissions rather than chunk continuation.
Its serving evidence is simulation, including production-trace replay; it does
not demonstrate correctness or speed on this GLM/GB10 runtime.
[SLOWeave](https://arxiv.org/pdf/2609.07883) separates queue selection from chunk
sizing and selects work against decode deadlines. Its guarantee depends on an
accurate cost predictor and feasible decode-only service; overload can starve
prefill. These are alternatives to investigate, not proven fixes here.

After the Exa lookup, inspected local vLLM scheduler token/long-prefill budgets,
exllamav3 generator/job chunk bounds and retained MTP carry, TensorFold
`prompt_fill.py` shortest-remaining selection with passed-chunk guard and decode
round credit, and pinned FlashInfer A16/A4 execution ownership. Flare's current
completion key uses arrival time plus estimated remaining service. Age continues
to accrue while service runs; old long work can keep outranking later short work.
Changing cohort membership also changes candidate value and graph competition,
even when decode price coefficients remain unchanged. Both are hypotheses until
native mixed trace evidence establishes the actual service sequence.

Stronger follow-up options are bounded promotion, preserving balanced selection
when decode is active, and deadline-aware chunk sizing. Naively resetting age on
every chunk can reintroduce equal-prompt interleaving; forcing every eighth chunk
can do likewise. Do not transplant either without CPU and live mixed coverage.

## Registered diagnostic window

Window `mixed-trace-window-20261116T031600Z`, independent variable balanced versus
latency; same immutable artifact406f7d03, coredf214696, checkpoint, TP2,4slots,
MTP3,chunk4096,CP-off,reserve4,T1/.95 and unchanged native observer. No native
code/build, memory reserve, quantization or KV change. Cold restart each arm.

The client adds explicit `--reps 1` for bounded diagnostics; default remains3.
One rep retains all three original cases and25 requests, with the same run-id
`scheduler-latency-20261116` so rep0 bodies match the retained untraced receipts.
The performance comparator still rejects any one-repetition receipt (regression
covered by a test). No traced timing is a production performance verdict.

Before stop, snapshot ledgers and identities, freeze client bytes in Git, arm a
60-minute B12X restoration timer, and disarm B12X watchdog. Use the unchanged
90GiB-free/100GiB-available idle gate on both nodes. Start only through the native
unit. Verify executable, core, actual argv and head-only trace before each client.
Enforce1.5GiB-free/8GiB-available during both arms; any violation queues restoration.
The restoration helper stops this window's orchestrator and both memory units.

For each arm require the client to complete25 requests/3 cases with no errors,
matching rep0 body hashes, cold usage and observed overlap. Stop both native
ranks, retain invocation-bound native exit0/no forced kill, then validate the
trace footer: no drops/truncation, complete counts and contiguous histories.
Inspect short-arrival generations and prefill graph durations during decoding.
Native slot generations are not HTTP IDs; infer only where lengths/order uniquely
identify histories, and label any ambiguity. Missing/truncated observation fails
the diagnostic and does not justify a scheduler edit.

Automatically restore B12X after both captures or on error. Retain original
images, health200, fresh smoke5/5 and watchdog/tailnet verification before
appending rollback selection and disarming fallback. No production adoption,
boot change or merge until all previously registered gates pass.
