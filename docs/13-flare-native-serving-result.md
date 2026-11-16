# Native-activation Flare serving result — 2026-11-16 UTC

The completed three-repetition matrix **fails the registered concurrent prefill latency gate**. Decode aggregate throughput improves 7.4–13.9%, but 14 of 20 prefill points have separated per-request regressions of 7.6–37.5%. Aggregate prefill throughput stays within −1.8% to +2.0% of B12X. Faster aggregate work does not cancel the TTFT failure. No adoption.

Runtime arm: frozen launcher f6a8f3e; Flare `5a4e867`, FlashInfer `4fd836dc`, checkpoint `76348ddb`; native-activation core df214696. Both engines use TP2, four execution slots, fixed MTP-3, prefill 4096, temperature 1/top-p .95, identical request bodies and tokenizer. Flare retains CP-off and reserve 4. The candidate client produced all 84 rows; strict comparison validated 315 matching request hashes, 225 exact cold prefills and 90 decodes of 200 tokens per engine. All three repetitions remain in the raw receipts.

## Decode aggregate throughput

Median of three repetitions; tok/s includes request startup and queueing. Per-request decode rates, speculative deltas, acceptance lengths and every repetition are retained in the comparison JSON.

| Concurrency | Prompt | B12X tok/s | Flare tok/s | Change |
| --- | --- | ---: | ---: | ---: |
| 1 | code | 34.46 | 37.32 | +8.29% |
| 1 | prose | 34.78 | 38.01 | +9.28% |
| 2 | code | 48.15 | 53.68 | +11.49% |
| 2 | prose | 45.47 | 49.66 | +9.20% |
| 4 | code | 68.26 | 73.31 | +7.41% |
| 4 | prose | 64.11 | 71.20 | +11.06% |
| 8 | code | 64.96 | 73.99 | +13.90% |
| 8 | prose | 63.65 | 71.54 | +12.41% |

## Prefill latency

TTFT below is the median of the three within-batch medians, in seconds. The gate uses the separately calculated per-request prompt_tokens/TTFT rate; for even batches, its median is not the reciprocal of median TTFT. Concurrency 8 includes queueing behind four execution slots. “Fail” means even the best candidate repetition has a rate below 98% of the worst reference repetition.

| Concurrency | Prompt tokens | B12X TTFT s | Flare TTFT s | Prefill rate change | Gate |
| --- | ---: | ---: | ---: | ---: | --- |
| 1 | 8192 | 3.55 | 3.49 | +1.85% | No >2% regression observed |
| 1 | 16384 | 7.14 | 7.02 | +1.73% | No >2% regression observed |
| 1 | 32768 | 14.41 | 14.15 | +1.84% | No >2% regression observed |
| 1 | 65536 | 29.18 | 28.61 | +2.01% | No >2% regression observed |
| 1 | 131072 | 59.51 | 58.34 | +2.01% | No >2% regression observed |
| 2 | 8192 | 6.17 | 6.09 | +1.38% | No >2% regression observed |
| 2 | 16384 | 11.60 | 13.17 | -16.24% | Fail |
| 2 | 32768 | 22.49 | 27.43 | -24.40% | Fail |
| 2 | 65536 | 44.57 | 56.31 | -28.22% | Fail |
| 2 | 131072 | 90.19 | 116.76 | -30.63% | Fail |
| 4 | 8192 | 10.62 | 11.78 | -11.79% | Fail |
| 4 | 16384 | 19.64 | 25.75 | -26.17% | Fail |
| 4 | 32768 | 37.78 | 54.17 | -32.76% | Fail |
| 4 | 65536 | 74.65 | 112.62 | -36.23% | Fail |
| 4 | 131072 | 150.37 | 231.11 | -37.47% | Fail |
| 8 | 8192 | 17.71 | 20.58 | -14.62% | Fail |
| 8 | 16384 | 33.91 | 39.59 | -7.58% | Fail |
| 8 | 32768 | 66.62 | 82.65 | -13.06% | Fail |
| 8 | 65536 | 133.08 | 169.72 | -13.56% | Fail |
| 8 | 131072 | 269.35 | 347.86 | -14.67% | Fail |

## Correctness, memory and closure

The preceding native API smoke passed 7/7 and the component arm passed 49/49 with unchanged numerical bounds. Those narrow checks do not close full-model precision, cold/forked retrieval, cache-pressure, ordinary/speculative parity or long-context admission. Reported KV capacity remains 2,295,552 versus B12X 2,350,210, a 2.33% shortfall.

The serving memory monitor collected 1,035 two-node observations from 22:43:23 UTC to 00:15:39 UTC without observation errors or threshold violations. Observed minima: head 2.036 GiB free/10.355 GiB available; worker 1.766 GiB free/10.857 GiB available. These are sampled minima, not instantaneous peaks. Enforcement stopped deliberately before lifecycle work.

The loaded graceful-shutdown client failed its preflight before creating a stream or sending a signal: it requested six systemd properties but required seven returned fields. The preserved traceback is a client defect, not evidence of native shutdown failure. The local fix validates the exact six names and rejects empty/missing/substituted fields; 42 local tests pass. It has not yet been rerun on hardware. Restoration then stopped both services with recorded status0. Subsequent supervisor inspection found that requested stops masked native child failures, so those statuses do not independently prove native exit0. See docs/21 for the corrected per-invocation evidence. That idle stop does not qualify loaded shutdown or peer-failure propagation.

B12X restoration started through the pre-armed helper at 00:16:13 UTC. At 00:22:21 UTC, health was 200, both nodes used the original image, and the watchdog and tailnet service were active. The fresh smoke passed 5/5; the restoration timer was disarmed only after verification at 00:22:59 UTC. Full retrieval and peer-failure checks were deferred after the speed gate failed. The previous core and all failed evidence remain retained.

## Exa investigation and next candidate

[Official scheduling design](https://github.com/NVIDIA/spark-local-inference/blob/main/docs/scheduling-runtime-design.md) describes prompt-token service fairness and useful-value/time scheduling. Pinned local policy.rs sets `token_fairness=16`; its throughput policy only removes delivery fairness and decode-age pricing, retaining prompt-token fairness. Consequently, switching to throughput alone is not a source-supported fix for pure concurrent prefill latency. The observed TTFT pattern is consistent with interleaved prompt progress; scheduler tracing is still needed to establish causality.

The [CLI contract](https://github.com/NVIDIA/hyperflare-inference/blob/main/docs/cli-design.md) exposes scheduler policy and chunk size, while [NVIDIA chunked-prefill guidance](https://developer.nvidia.com/blog/streamlining-ai-inference-performance-and-deployment-with-nvidia-tensorrt-llm-chunked-prefill/) explains the TTFT/decode-interference tradeoff. Local vLLM running-request scheduling, exllamav3 prompt/state ownership and TensorFold chunk scheduling were reviewed. TensorFold bounds skipped prompt chunks to avoid starvation; a completion-oriented prefill preference must preserve such progress guarantees and decode cadence. None of these sources proves a Flare improvement without a separate frozen arm and full gate.

[Official systemctl documentation](https://freedesktop.org/software/systemd/man/latest/systemctl.html) confirms selected-property machine-readable output and --all for empty fields, supporting the lifecycle-client correction. No native scheduler, kernel, cache layout, driver or memory reserve changed during this window.

## Receipts

- [Matched comparison](../receipts/flare-qualification-20261115/native-activation-comparison.json)
- [Candidate raw matrix](../receipts/flare-qualification-20261115/native-activation-full-bench.jsonl)
- [B12X raw matrix](../receipts/flare-qualification-20261115/reference-full-bench.jsonl)
- [Candidate exit state](../receipts/flare-qualification-20261115/native-activation-benchmark-terminal.txt)
- [Two-node memory samples](../receipts/flare-qualification-20261115/native-activation-memory.jsonl)
- [Lifecycle preflight failure](../receipts/flare-qualification-20261115/native-activation-lifecycle-preflight-failure.txt)

- [Restored runtime identity and health](../receipts/flare-qualification-20261115/native-activation-restored-runtime.txt)
- [Restored B12X smoke](../receipts/flare-qualification-20261115/native-activation-restored-smoke.txt)
