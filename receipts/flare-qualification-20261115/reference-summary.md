# Completed B12X reference — 2026-11-15

The client unit exited successfully at 21:30:56 UTC after 90m31s. Production
remained healthy with its original image on both nodes and watchdog active.
This is the reference arm, not a completed Flare comparison or adoption gate.

Validated 84 measurement rows (three repetitions): 225 exact raw-token prefill
requests, all observed cached tokens zero; 90 decode requests, all 200 tokens.
All 315 request hashes are distinct. Seed 20261115, temperature 1, top-p .95,
four-slot cap, and the pinned checkpoint tokenizer are frozen for Flare.
Receipt SHA256: `84c2865f80cdbda06eaa5d86e9d577866a70ff3e4ed61da534b3420a867bfefd`.

## Decode

Aggregate throughput includes request startup and queuing. Acceptance is derived
from each batch's counter delta. Values below retain all three repetitions.

| Concurrency | Task | Aggregate tok/s, reps 1 / 2 / 3 | Acceptance length, reps 1 / 2 / 3 |
| --- | --- | --- | --- |
| 1 | prose | 35.46 / 34.78 / 33.12 | 2.584 / 2.551 / 2.398 |
| 1 | code | 34.46 / 35.49 / 33.84 | 2.519 / 2.618 / 2.457 |
| 2 | prose | 45.47 / 46.56 / 43.58 | 2.412 / 2.503 / 2.314 |
| 2 | code | 48.15 / 53.16 / 45.17 | 2.653 / 2.863 / 2.472 |
| 4 | prose | 64.11 / 63.10 / 64.15 | 2.584 / 2.464 / 2.464 |
| 4 | code | 70.56 / 63.22 / 68.26 | 2.627 / 2.527 / 2.717 |
| 8 | prose | 63.19 / 63.65 / 67.61 | 2.387 / 2.461 / 2.527 |
| 8 | code | 64.11 / 64.96 / 66.78 | 2.618 / 2.568 / 2.631 |

## Prefill

Median of per-request prompt-tokens/TTFT across all three reps, including queue
wait. Concurrency 8 exceeds the four-slot cap; do not interpret its queued rate
as single-request engine throughput. Raw TTFT, elapsed time and batch wall time
are retained in `reference-full-bench.jsonl`.

| Concurrency | 8192 | 16384 | 32768 | 65536 | 131072 |
| --- | --- | --- | --- | --- | --- |
| 1 | 2305.72 | 2295.86 | 2273.43 | 2245.56 | 2202.35 |
| 2 | 1354.54 | 1488.27 | 1579.15 | 1619.84 | 1618.71 |
| 4 | 793.30 | 862.37 | 899.91 | 912.27 | 905.95 |
| 8 | 466.92 | 488.36 | 497.27 | 498.97 | 491.81 |

Decode variability is material in some groups, especially concurrency-2 code.
Use paired same-fixture results and retain per-repetition outcomes; extend the
registered comparison to five repetitions if the candidate conclusion is noisy.
No speed-preservation decision is made from these reference numbers alone.

A single observation during this run found about 2.9 GiB MemAvailable per node;
it is not a measured full-run minimum. No physical-memory improvement is claimed.
