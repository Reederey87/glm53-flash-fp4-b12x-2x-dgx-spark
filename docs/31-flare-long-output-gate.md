# Long-prompt output qualification

The bounded policy resumes balanced competition while decoding is live. Its
single-output prompt tests therefore cannot establish gains on longer outputs.
This extends docs/26's already required long-output check; it does not replace
the mixed or full speed matrices.

Exa reviewed [vLLM's measurement definitions](https://docs.vllm.ai/en/latest/benchmarking/cli/)
and [input/output workload controls](https://docs.vllm.ai/en/stable/cli/bench/serve/).
Speculative output arrives in bursts: delivery gaps must not be relabeled as
per-token latency. Local vLLM benchmark output accounting, exllamav3's shared
prefill chunk/cooldown and TensorFold's decode time share were inspected before
implementing this client. These mechanisms support measuring interference; they
do not predict this candidate's hardware gain.

Use `scripts/flare_long_output.py run` on fresh balanced and bounded-latency
starts, with the same run ID and tokenizer. Freeze native/core/checkpoint,
reserve, four slots, MTP3, chunk4096, CP-off, T1/.95 and tracing off. Warm once.
Run three repetitions of four barrier-synchronized cold prompts with lengths
131072/32768/8192/4096 and256 generated tokens each. Preserve exact request
hashes, actual cold usage, complete SSE termination, all delivery timestamps and
per-batch speculative counter snapshots. A short output or incomplete request
is a failed workload, not a throughput pass. Do not publish raw prompts/output.

The comparator requires all12 matching requests per arm and reports every
role's TTFT, completion time and95th-percentile/maximum output-delivery gap,
plus cohort completion time. Use the existing descriptive2% rule: separated
regression fails; overlapping bad medians require investigation/repetition.
No automatic adoption from this client or from aggregate throughput alone.
Numerical, semantic, capacity and state gates remain separate.

Do not inject this workload into a running performance matrix. Register exact
unit names, snapshots and a bounded B12X restoration timer before its separate
window. Both-node idle90GiB free/100GiB available and serving1.5GiB free/8GiB
available limits remain. Verify actual runtime identities and API smoke before
measurement, native exits before switching, then original B12X images, fresh5/5
smoke and watchdog/tailnet before disarming restoration. This document records
the unrun test and original gate, not measured gains.
