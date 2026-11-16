# Fixed-output stress retry

The initial docs/37 balanced arm completed rep0 but rep1 failed the256-token
completeness assertion. Latency never ran. Retain `long-output-initial-*` receipts:
45 memory samples pass, both native exits0/no forced kill, B12X independently
restored06:17:25 UTC with5/5 smoke and fallback disarmed. The old batch client
lost the failed request's usage and finish reason. Natural EOS is a possible
cause, not an established diagnosis.

Exa reviewed NVIDIA's [API stop semantics](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/api.md)
and [benchmark contract](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/cli-design.md).
`ignore_eos` continues through sampled EOS without changing proposals, sampling
or speculative acceptance. A capacity-limited request can still end early;
therefore finish_reason=length alone is insufficient: exact256 usage remains
mandatory. A min-token/logit-mask change would alter the workload distribution
and is unnecessary. Pinned native protocol decode/runtime implement this option.
vLLM's serving benchmark uses the same option; exllamav3 separates stop-token
conditions, and TensorFold forwards ignore_eos to its GLM request stop policy.
No engine replacement or serving arithmetic change is required.

Schema2 adds ignore_eos=true to both arms, preserving the prompt generator,
lengths, three repetitions, seeds, T1/.95 and256 output budget. Use a new run ID,
`long-output-eos-20261116`; never compare schema1 and2. An independent flushed
per-request sidecar preserves usage, finish reasons, delivery timings, hashes,
DONE status and transport error class before validation. No generated text is
retained. Partial batches still fail and produce no aggregate comparison.
Local tests reject short output, stop-policy changes and malformed receipts,
and prove partial observations survive both normal EOS and transport failure.

Register `long-output-eos-window-20261116T100000Z` after the two-host layer window
has independently restored B12X and disarmed its fallback. This independent
performance workload does not waive any layer failure or mixed-performance gate.
Frozen native127424e9/binaryb2eb310b/core df214696/wrapper41b65a5a/reserve4,
TP2/four slots/MTP3/chunk4096/CP-off/trace-off remain. Only scheduler policy
changes between fresh balanced and latency arms. The client manifest freezes
new hashes. Existing2% and repetition-range classifications remain unchanged.

Helpers in `qualification/windows/long-output-eos-20261116` retain docs/37's
60-minute restore timer,50-minute orchestrator limit, idle and memory guards,
7/7 API checks and both actual native exits0/no forced kill after each arm.
Record live capacity; this workload cannot waive its adoption floor. Restore
B12X after completion or failure; require independent5/5 smoke, both original
images, API/watchdog/tailnet and absent native PIDs before disarming fallback.

## Result

Both arms completed12/12 requests with exactly256 output tokens and length
finish reasons. Both actual native exits0 without forced kill;70 memory samples
per policy pass. Local strict recomputation matches remote comparison. Of17
points,13 show no median regression over2% and four require repetition with
overlapping ranges; none is separated. Cohort median119.258→119.561s (+0.254%),
128k TTFT104.135→105.584s (+1.39%). Unresolved:32k TTFT+7.31% and elapsed+2.97%,
8k p95 delivery gap+2.36% and maximum gap+4.91%. This does not close the original
mixed/full performance gate. Full observations and per-request sidecars are
retained as `long-output-eos-*`. Recovery verification is pending separately.

Recovery subsequently passed independent5/5 B12X smoke, original images on both
nodes, healthy API/watchdog/tailnet and absence of native processes. Exact
restore/smoke invocation IDs and terminal statuses are retained in
`long-output-eos-restoration-verified.txt`; fallback disarm follows in its own
receipt. This closes the window, not the unresolved performance points.
