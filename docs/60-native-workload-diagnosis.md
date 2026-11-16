# Complete native workload diagnosis

Docs/55 completed all four registered starts by10:50 UTC:174 measured requests,
four warmups,178 complete native histories and5,394 contiguous completions.
Every trace stops cleanly with zero loss/truncation; both ranks exit0 without
forced kill on every arm. All411 continuous memory observations pass. Minimum
free/available GiB: head1.8389/10.6190; worker1.7210/11.4557. Startup pools are
2,343,168 for the first arm and2,335,232 thereafter, still below adoption capacity.
B12X restoration and its independent smoke are underway; fallback remains armed.

The workload is matched for diagnosis, but starts and warmup history differ from
the untraced ABBA (docs/55's registered limitation). The traces do not replace its
failed80-point gate or qualify a performance improvement. Diagnostic HTTP
comparisons and all raw traces are retained as`abba-trace-*`.

## Observed mechanisms

1. **Cold discovery postpones terminal completion.** In the first balanced
   unequal burst, the4k prompt finishes native prefill at fence11, then waits
   7.3312seconds until snapshot fence21. Eight previously unseen prefill sizes
   and initialization execute in between. The latency arm also waits5.9331seconds
   between its first4k prefill and snapshot. HTTP first-token-to-end intervals
   agree to millisecond scale for the unique4k requests in those cohorts. Later
   repetitions do not show the same multi-second discovery tail.

2. **Prefill shape/history affects decode gaps.** Mixed balanced service uses
   ordinary2,048-token graphs during several observed gaps. Latency service later
   uses a2,560-token timing-refresh probe and then ordinary2,560-token work,
   producing approximately1.3-second native decode gaps. The mixed short prompt
   has separated adverse diagnostic TTFT/elapsed distributions. Long-output
   traces also contain ordinary3,584-token prefill during live decode, producing
   approximately1.66–1.68-second gaps in both policies. Other gaps contain an
   ordinary prefill followed by a funded refresh probe. The trace identifies
   intervening work; it does not isolate a policy-byte effect from the different
   preceding timing/admission histories. The existing completion-order override
   is disabled while Decode/Resume requests are live.

3. **Visible chunks are not native token progress.** The128k latency requests'
   maximum visible-text gaps are0.133/0.117/0.204seconds versus
   0.072/0.072/0.074seconds for balanced. Their native decode completion gaps stay
   near0.070–0.073seconds on both arms, with no intervening prefill at those
   largest native gaps. All generate256 tokens, but latency exposes253/255/254
   nonempty text chunks versus balanced255/256/256. This is consistent with
   presentation/buffering or event delivery rather than a corresponding GPU
   pause; the existing receipts lack raw token-to-presentation correspondence,
   so the cause is not yet proven. Preserve the visible gaps, not relabel them.

## Source checks and next treatments

Exa reviewed NVIDIA's [scheduling implementation](https://github.com/NVIDIA/flare-local-inference/blob/main/helios/src/scheduler/policy.rs),
[scheduling design](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/scheduling-runtime-design.md),
[token observation contract](https://github.com/NVIDIA/flare-local-inference/blob/main/helios/model-contract.md)
and [HTTP listener](https://github.com/NVIDIA/flare-local-inference/blob/main/helios/src/server/listener.rs),
plus official [vLLM chunked-prefill guidance](https://docs.vllm.ai/en/stable/configuration/optimization/).
Pinned source confirms unknown-duration candidates outrank measured ones before
value comparison, so raising terminal value alone cannot repair cold discovery.
TCP_NODELAY is already enabled on accepted serving sockets; do not add a redundant
network fix. Output decoding can withhold text or omit EOS presentation.

Native token IDs/timestamps provide a stronger observation boundary before output
parsing, but the documented SSE interface is for chat, not the raw completion
workload used here. They are host completion timestamps, not GPU execution or
socket delivery. A future observation probe must respect that scope; it cannot
retroactively identify the missing raw token presentation from these traces.

Local review covered Flare cost refresh/candidate selection and presentation,
vLLM's decode-prioritized token budget, exllamav3's separate shared-prefill chunk
limit, TensorFold's shape-specific warmup/cost measurement and unchanged FlashInfer
operators. Smaller chunks can improve decode cadence while hurting prompt
throughput; that tradeoff needs measurement. A cap must also cover funded refresh
and queued work, not only ordinary candidates.

Docs/59's bounded warmup is the first isolated startup proposal; its client is
prepared, unrun and absent from production startup. A decode-aware prefill/refresh
limit is a separate possible treatment, not yet implemented. Complete token
publication evidence before assigning the visible-only gaps to scheduling.
Freeze each next treatment and its gates before execution. The failed ABBA,
full84-row comparison, numerical/state, capacity and production/reboot requirements
remain open. No production adoption or main merge follows this diagnostic pass.
