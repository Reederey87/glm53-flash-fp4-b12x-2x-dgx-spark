# Bounded scheduler mixed result — unresolved

Window `bounded-retry-window-20261116T050000Z` completed all 75 requests and
nine cases in each arm. Both used artifact 127424e9 / binary b2eb310b, corrected
supervisor 41b65a5a, core df214696, four slots, MTP3, prefill 4096, reserve 4,
CP-off and tracing off. The control's two native processes exited 0 without
forced kill. Both starts passed seven API checks. All sampled memory gates
passed. Actual startup pools were 2,335,232 and 2,331,392 tokens respectively;
both remain below the unchanged capacity floor.

Of 61 registered comparison points, 36 meet the descriptive median criterion
and 25 require investigation/repetition. None is a separated >2% regression
under the registered range rule. This is not a pass: the runner returned 1 and
queued B12X restoration at 05:16:26 UTC. The full 84-row matrix did not run.

Selected retained medians:

| Workload/metric | Balanced | Bounded latency | Change |
| --- | ---: | ---: | ---: |
| Unequal burst, 131072-token TTFT |79.812s|79.495s|−0.4%|
| Unequal burst, 32768-token TTFT |35.009s|20.118s|−42.5%|
| Unequal burst, 8192-token TTFT |12.490s|5.781s|−53.7%|
| Unequal burst, 4096-token TTFT |7.193s|1.719s|−76.1%|
| Decode-overlap cohort completion |39.864s|40.966s|+2.8%|
| Decoder 0 p95 delivery gap |0.10065s|0.34851s|+246.3%|
| Short-arrival request 5 TTFT |1.30655s|2.44913s|+87.5%|

The earlier 36-second late-short stall did not recur: the maximum short-arrival
TTFT in this bounded run was 3.002s. However, that does not erase the unresolved
medians. Decoder 0's amortized decode rate improved 2.7%, and its median maximum
gap improved 13.5%; these other metrics cannot replace its failed p95 criterion.

## Investigation, without changing the gate

The p95 is near a mixture boundary. Decoder 0 has about 511 observed gaps per
request. Balanced has 23/24/23 gaps over 0.2s; bounded has 27/20/26. The 95th
percentile therefore moves from the ordinary delivery cadence into the slower
prefill-interference population in two bounded repetitions. This explains the
percentile's sensitivity, not the scheduling cause or acceptability of the extra
pauses. The bounded maximum reaches 2.541s in another repetition and is retained.

Periodic short arrivals also have two visibly different timing patterns across
repetitions in both arms. Their ranges overlap. Native dispatch evidence is
needed before blaming a particular graph choice, timing-model history or
arrival phase. Do not apply another scheduler patch from these HTTP timings.

Exa reviewed [vLLM's burst/latency measurement definitions](https://docs.vllm.ai/en/latest/benchmarking/cli/),
[arrival and warmup controls](https://docs.vllm.ai/en/latest/cli/bench/serve/),
[NIST blocking/replication guidance](https://www.itl.nist.gov/div898/handbook/pri/section3/pri332.htm)
and [SLO-aware chunk selection research](https://arxiv.org/html/2504.08784).
These support retaining full gap distributions, checking run-order effects and
tracing graph interference. They do not establish a GB10 gain or justify changing
the registered 2% rule. Deadline-aware chunk sizing is a stronger alternative,
conditional on a validated cost model; it is not this candidate.

Raw paired timings, comparison, startup metrics, control exits, memory samples
and descriptive gap counts are `bounded-retry-*` in
`receipts/flare-qualification-20261115/`. The independent expert arithmetic
window in docs/30 can proceed after verified restoration because it tests the
unchanged kernel/core precision path. Performance remains unresolved; no
production adoption, boot cutover or main merge is authorized by these results.
