# Candidate 2 — not qualified; control restored

**Decision: reject the allocator candidate at 17 GiB KV.** Larger 19/20 GiB
arms were not attempted because the pre-registered headroom condition failed.
No allocator throughput or mechanism conclusion is supported.

The complete control passed 5/5 functional checks, all 20 exact-token cold
prefill cells at c1/2/4/8, and 12 strict post-ladder decode batches. Four-seat
queueing is included at c8. Median aggregate decode: 38.107 / 55.402 / 82.466 /
77.288 tok/s; acceptance rates 0.5753 / 0.6211 / 0.6280 / 0.6126.

The reviewed allocator-only retry started 2026-11-10T23:52:10Z. During startup,
the worker reached **2,053,508 KiB available (1.958 GiB)** at 23:56:31Z,
breaching the **2 GiB** pre-registered floor. The independent observer stopped
production; the driver cancelled startup and restored the default allocator.

| Sampled minimum available | Head | Worker |
|---|---:|---:|
| Complete control window | 2.031 GiB | 2.235 GiB |
| Incomplete B startup | 2.848 GiB | 1.958 GiB |

These are sampled host-memory minima over different completed phases, **not a
paired steady-state headroom comparison**. B did not reach post-health activation
verification or functional/speed smoke. There is no complete B matrix, no speed
comparison, and no evidence to raise KV. Do not interpret the abort as a measured
allocator performance regression or attribute an unverified internal mechanism.

Recovery completed **2026-11-11T00:02:40Z**: primary status 1 (safety rejection),
recovery status 0; `/health` 200; smoke 5/5; pinned image and absence of allocator
override verified on both ranks; KV 2,350,210; serving unit, watchdog and proxy
individually active. The temporary recovery ENV_FILE override is removed.

An earlier administrative dispatch failed before engine launch because the
pinned upstream rejects duplicate env keys. The derived-config fix preserves the
append-only ledger and passed the actual pinned validator and serialized B/A
frontend dry-runs. A separate false teardown failure from failed-inspect blank
stdout was fixed and regression-tested. Neither repair changes inference flags.

Validation: 10 CPU tests and 11 isolated user-systemd failure scenarios passed.
All cluster/API commands in the lifecycle scenarios were mocked; the actual
safety abort and actual recovery above were observed on the cluster. Preflight
review cleared the final critical code at `90c92da` for this experiment only.
