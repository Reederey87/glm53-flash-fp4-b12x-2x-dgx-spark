# Additional scheduler evidence — Exa review, 2026-11-16 UTC

The proposed change targets waiting time before the first response. It does not
claim faster kernels, less prompt work, or higher aggregate throughput. The native
CPU selector reproduces the observed interleaving, and its opt-in treatment
improves completion order. Hardware performance remains unqualified.

## Evidence and limits

| Primary source | What it supports | Limitation and consequence for this candidate |
| --- | --- | --- |
| [Aging and remaining-work scheduling](https://arxiv.org/html/2606.09061v1) | Request age plus remaining prefill work can reduce queueing while protecting older requests. Its measured execution time was essentially unchanged. | Its single-GPU aging experiment used RTX4090, maximum context512 and short ShareGPT prompts. Benefits weakened at larger chunks, with a small mean-latency regression at1024. It does not predict GLM/GB10/128k results or justify copying its coefficients. |
| [Lightweight scheduling across GPUs](https://arxiv.org/html/2610.15899) | Across1152 GPU/model/scheduler/workload runs, simple age-aware short-job policies were competitive; scheduler choice affected throughput and tails. | The testbench uses smaller models, L40S/A100/H100 and different execution/batching. Oracle remaining-output scheduling was not universally better. This supports mixed-workload validation, not a numerical speed claim here. |
| [Sarathi-Serve](https://arxiv.org/html/2403.02310) | Prefill/decode interference matters; prompt gains cannot substitute for uninterrupted generation and tail-latency checks. | Its mixed batching and hardware differ from the prepared separate GLM graphs. Keep chunk4096 and decode pricing fixed in this arm; do not combine a larger chunk or mixed capture with prompt ordering. |
| [vLLM concurrent partial-prefill PR](https://github.com/vllm-project/vllm/pull/10235) | Strict serial long-prefill service can harm short arrivals. Controlled overlap can improve heterogeneous workloads. | This was explicitly the old V0 scheduler. Current local V1 and [current configuration](https://docs.vllm.ai/en/stable/api/vllm/config/scheduler/) contain long-prefill token caps but not those old partial-prefill-count flags. They are not a current drop-in fix. |
| [Flare native scheduling design](https://github.com/NVIDIA/spark-local-inference/blob/main/docs/scheduling-runtime-design.md) | Balanced and throughput retain token-service fairness; feedback and terminal retirement compete through native selection. | Throughput alone does not remove the observed pure-prefill interleaving. Disabling fairness indiscriminately has no starvation guarantee. Preserve the other stages and test their interaction. |

The proposed key is `arrival + remaining_tokens * measured_chunk_time/chunk_tokens`.
Subtracting current time from every request's key gives remaining estimated
service minus request age. Unlike shortest-remaining-work alone, an older request
can overtake a continuing stream of new short requests. This is a conditional
progress preference under finite active slots and bounded positive cost estimates,
not a hard latency deadline under arbitrary overload. Cold timing uses the
existing discovery path. Cost drift and nonlinear context costs remain reasons
to require live measurements.

After Exa, local vLLM's running-budget loop and long-prefill caps, exllamav3's
shared-chunk/cooldown mechanism, FlashInfer's unchanged A16/CSF preparation and
TensorFold's `_next_fill` were reviewed. TensorFold prefers less remaining work
but forces a turn after eight skipped chunks. The candidate adopts remaining-work
selection with continuous arrival aging; it does not copy the fixed guard or
replace either serving engine. This avoids adding a model-specific token threshold.

## Alternatives considered

- Throughput preset: retains the relevant fairness term, and the native CPU
  control produces the same interleaved order. It remains useful for a distinct
  decode-cadence experiment, not this prompt-latency diagnosis.
- Strict FIFO or one active prefill: can improve equal-length bursts, but allows
  a long head request to block later short prompts. The candidate's unequal-length
  and continuing-arrival tests specifically protect against that substitution.
- Shortest remaining work without age: lower mean completion time can come at
  the expense of old long requests. The native sustained-arrival test requires
  the long request to progress and finish while short requests continue arriving.
- Larger chunks: a separate capture/export change, with decode-interference and
  memory costs. It is not combined with this host-policy treatment.

## Required empirical qualification

Already observed:317 native scheduler tests,2 config tests and1 CLI test passed;
two manual CPU planning benchmarks were ignored and are not counted. Tests cover
equal/unequal lengths, continuing short arrivals, cancellation, unknown estimates,
active speculative decode and two-in-flight feedback.45 local tests cover the
launcher and qualification clients. These do not prove GPU speed or accuracy.

The next live arm must retain the exact core, checkpoint, quantization, KV reserve,
four slots, MTP3, chunk4096 and sampling. Verify both binaries and the selected
policy before the full matched three-repetition8k..128k c1/2/4/8 matrix. Preserve
the existing >2% robust-regression rejection rule; record individual TTFTs and
last-response completion, not just aggregate throughput.

Also compare mixed long/short arrivals and prompts overlapping active decode on
the same core with balanced versus latency. Require cold prompt counts, actual
arrival offsets and request hashes, complete output budgets, per-request TTFT,
visible streaming-delivery gaps and completion times. Speculative output may
arrive in bursts: call those delivery gaps, not per-token latency. A missing
overlap observation or early output termination makes the case inconclusive.
No unexplained >2% robust regression of decode throughput or delivery-gap tails;
no stalled long request, cancellation leak, corrupt output or rank failure.
Register concrete workloads and client bytes before execution. The matched
equal-length matrix cannot stand in for these mixed-workload checks.

Full-model numerical, long-context admission/retrieval and loaded shutdown remain
separate gates. Only their passing evidence permits the authorized adoption and
boot/reboot qualification. The supporting papers are a rationale for this
experiment, not evidence that the production outcome has been achieved.
