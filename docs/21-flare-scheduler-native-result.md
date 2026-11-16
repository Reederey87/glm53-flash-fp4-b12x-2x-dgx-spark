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
