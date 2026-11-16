# Native scheduler evidence and additional Exa review

On 2026-11-16 UTC, the balanced policy completed the registered cold four-request
131072-token diagnostic on both Sparks. The unchanged core and native binary
6686043d were verified from the running processes. The client exited0 with its
terminal state retained. The trace validator accepted353 native completions,
zero dropped updates, no truncation and complete contiguous histories for all
four prompt generations. Raw receipts are under
`receipts/flare-qualification-20261115/scheduler-balanced-*`.

The first prompt finished after520576 of524288 cohort prompt tokens had been
processed (99.29%). The remaining finishes occurred at521472,522240 and524288.
Client TTFTs were233.52,234.21,234.88 and235.96seconds. This directly confirms
interleaved prompt service for this workload; HTTP timestamps alone had only
suggested it. Native identities are slot/generation pairs, with no invented
mapping to HTTP requests. Traced timings are diagnostic, not an untraced speed
result or evidence that the latency treatment passes.

The same trace also records a modest context-cost increase. For complete4096-token
single-lane prefill chunks in the four validated histories, median observed GPU
duration is1.773,1.804,1.840 and1.875s across successive32k start-position bins
(28/30/32/28 observations). The last median is5.75% higher than the first.
`scheduler-balanced-duration-bins.json` retains every duration and the raw trace
hash. These are max-rank CUDA intervals, not GPU start timestamps or utilization.
This supports checking cost calibration under long context; it does not justify
tuning coefficients from one diagnostic or claiming that kernel work decreased.

## Additional primary-source evidence retrieved with Exa MCP

- [Aging and remaining-work scheduling](https://arxiv.org/html/2606.09061)
  supports changing queue order without accelerating execution. It also reports
  a counterexample: at1024-token chunks, mean E2E increased from109.38 to110.59s.
  At256 it improved from118.72 to106.56s. Coefficients and gains cannot be copied
  into this4096-chunk,128k-context GLM/GB10 deployment. Keep the mixed-arrival
  and decode-interference rejection gates.
- [NVIDIA's chunked-prefill explanation](https://developer.nvidia.com/blog/streamlining-ai-inference-performance-and-deployment-with-nvidia-tensorrt-llm-chunked-prefill/)
  identifies a concrete tradeoff: larger chunks can improve prompt completion
  while delaying active decoding. This supports keeping chunk size fixed while
  testing order; changing both would obscure the cause.
- [SLOWeave](https://arxiv.org/html/2609.07883) is a stronger follow-up option:
  select the largest chunk predicted to fit before active decode deadlines.
  Its guarantee assumes an accurate monotone cost model and feasible decode-only
  work. Its simulator and A100/H100 dense-model runtime measurements do not
  establish GB10/GLM gains. Non-smooth graph boundaries, TP communication and
  predictor drift are explicit limitations. Flare already prices graph duration;
  assess prediction residuals before considering another controller. No adaptive
  chunking or additional capture is included in this treatment.
- [Flare's scheduling design](https://github.com/NVIDIA/spark-local-inference/blob/main/docs/scheduling-runtime-design.md)
  separates useful prompt progress from output cadence. Throughput retains token
  fairness; removing it globally is not a justified replacement for this targeted
  prefill ordering change. [Issue42](https://github.com/NVIDIA/flare-local-inference/issues/42)
  concerns feedback-window starvation already corrected in the pinned source;
  it is not another missing fix for this run.

After Exa, the local Flare remaining-work selector, vLLM V1 long-prefill budget,
exllamav3 shared-chunk/cooldown controls, TensorFold `_next_fill` remaining-work
selection with its skipped-turn guard, and FlashInfer tracing entry points were
reviewed again. They support separate decisions about prompt order and active
decode interference. None substitutes for the measured native completion stream.

## Shutdown evidence correction before further qualification

Inspection found that `flare_run.py` returned0 whenever shutdown was requested,
even if cleanup subsequently killed its native child. Earlier receipts establish
that the service stopped and memory recovered; their supervisor status does not
independently prove native exit0. Loaded graceful qualification remains open.

The corrected supervisor waits for the child and retains its actual return code,
forced-kill flag and shutdown request in an atomic per-invocation JSON receipt.
It returns failure for nonzero or signal termination. The lifecycle checker binds
receipts to the active systemd invocation and requires both native children to
exit0 without forced kill for graceful success. Missing/stale evidence fails.
Peer-loss injection necessarily lacks the SIGKILLed worker's final record.

Exa checked the official [Python subprocess contract](https://docs.python.org/3/library/subprocess.html)
and [systemd retention semantics](https://freedesktop.org/software/systemd/man/latest/systemd-run.html):
waiting populates native status, signals produce negative return codes, and
collected units cannot supply retained terminal evidence. The native executable,
policy, core and serving loop are unchanged. All61 local tests pass, including
native nonzero/signal/forced-kill outcomes and stale or incomplete receipts.
Freeze and stage these supervisor/client bytes before the next start; both
untraced policy arms use the corrected supervisor. Existing docs/18–20 gates,
restoration deadline04:57 UTC and rollback remain unchanged.

## Mixed comparison audit

Exa rechecked the [official vLLM latency definitions](https://docs.vllm.ai/en/stable/benchmarking/cli/)
against local `vllm/benchmarks/serve.py`: speculative streaming gaps and per-request
TPOT have different denominators. `flare_mixed_compare.py` validates all75 matched
request identities and9 completed cases per arm, including zero cache hits,
arrival offsets, complete output budgets, recomputed gaps and observed decoder
overlap. It preserves three repetitions for every request role and applies the
previously registered separated/median2% rules. It reports end-to-end completion
rate separately from inverse amortized TPOT `(tokens-1)/(elapsed-TTFT)`; neither
invents token timestamps inside a burst. Four additional tests reject incomplete,
corrupt or mismatched evidence and exercise both metric directions. All65 local
tests pass. This offline tool does not alter the already frozen live client.

## Untraced balanced control and guarded restoration

The balanced control passed7 API checks, then all75 mixed requests and9 cases
across three repetitions. The strict comparator independently validated the
complete receipt. All114 memory observations passed; minimum MemFree was
2,259,763,200bytes on the head and2,487,926,784bytes on the worker. Each overlap
case retained progress from both decoders. The balanced control alone does not
demonstrate improvement from latency policy.

On the idle transition, both actual native children exited0 without forced kill.
The head recorded a requested shutdown; the worker recorded no local signal
because it had already exited through coordinated native drain. The transition
verifier incorrectly required a local signal on both ranks, triggering automatic
B12X restoration at02:31 UTC before the latency policy was selected. Preserve
these receipts and do not count this as a loaded-shutdown run.

Exa's [upstream coordinated-stop contract](https://github.com/NVIDIA/spark-local-inference/blob/main/docs/orbit.md)
and pinned `flare-cli/src/main.rs::serve_peer` explain the behavior: rank zero
drains the group; peers can exit before a later explicit stop. The peer returns
success only after drain and transfer-service completion, with no shutdown error.
The corrected lifecycle checker requires a requested head shutdown and actual
exit0/no forced kill on both ranks, allowing either local-signal state on the
worker. Regression coverage includes that observed shape and still rejects an
unrequested head exit, native failure, forced kill and missing/stale evidence.
No native shutdown protocol or performance/numerical bound changed. The next
window must freeze this checker and requalify the loaded path; the latency
trace, mixed treatment and full speed matrix remain unrun.
