# Warmup-only startup experiment

> Full MTP replay is complete (docs/62). Further research is paused; warmup is staged but unrun. Current production and safe resume instructions: [docs/63](63-production-pause-checkpoint.md).

Prepared, unrun. This follows the completed docs/60 diagnosis and Exa review of
NVIDIA's [native cost discovery and funded refresh](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/scheduling-runtime-design.md).
Unknown graph costs win over known costs; refresh has an aggregate budget but
no individual-stall bound. Warmup addresses cold discovery only. A decode-aware
prefill/refresh ceiling and token-publication observation remain separate work.
Local review reconfirmed the pinned Flare selector, vLLM mixed-shape warmup,
exllamav3 chunk/batch/context warmup, TensorFold per-shape warmup before cost
measurement, and unchanged FlashInfer normalization operations.

## Prospective gate

`warmup-window-20261117T070000Z` holds the native artifact127424e9, core,
checkpoint, latency policy, four slots, MTP3, reserve4 and quantization fixed.
Baseline is a fresh start with the existing128-token client warmup. Candidate
is a fresh start with docs/59's fixed14-request warmup before that same client.
The sole treatment is added startup workload. Both run the same three-repetition,
75-request mixed corpus, including identical cold request bodies and budgets.
Tracing is enabled on both starts; there is no API pre-smoke to alter graph history.

Require full cold/count/stream checks, complete native traces with zero loss,
clean native exits on both ranks, continuous1.5GiB free/8GiB available floors,
and exact artifact/launch verification. Retain startup capacity as observed;
the separate2,350,210-token adoption requirement is unchanged.

Mechanism success requires: baseline first4k terminal interval contains a
discovery prefill; candidate has zero such intervening discovery prefills;
candidate prefill-to-snapshot interval is at most50% of baseline; added warmup
completes within300seconds. Retain all native graph intervals and HTTP observations.
If baseline does not reproduce the mechanism, report this gate inconclusive
rather than claiming an improvement. No rerun-until-pass policy.

One fresh start per arm diagnoses this startup mechanism; it cannot qualify
general performance. Traced timing, startup overhead and unknown-shape coverage
must remain visible. A subsequent untraced comparison must retain the2% robust
regression rule, decode gaps and speculative acceptance, and then the full84-row
B12X comparison. Neither a mechanism pass nor smoother terminal completion
waives other adverse measurements or the outstanding numerical/state gates.

## Window and recovery

Prepared controller under`qualification/windows/warmup-20261117/` requires the
preceding generation window's independently verified B12X recovery and closed
fallback. Snapshot both nodes, verify source manifests, disarm B12X watchdog,
stop both ranks and wait for90GiB free. Continuous notifying memory guard5100s,
bounded controller4800s, warmup300s, each mixed client580s, rollback timer90min.
Stage atomically after commit; never run from the Git checkout. After both arms,
restore original B12X, independently verify original images, API/watchdog/tailnet
and fresh5/5 before closing fallback. No production warmup is installed here.
