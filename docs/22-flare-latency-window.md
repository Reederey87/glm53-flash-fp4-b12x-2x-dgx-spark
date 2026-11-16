# Latency treatment window — registered 2026-11-16 UTC

Continue docs/18–21 after independently verified B12X restoration at02:37 UTC.
Reuse the completed balanced native trace and untraced mixed control; do not
rerun an unchanged control merely because the guarded transition closed its
window. Native artifact406f7d03, binary6686043d, native-activation coredf214696,
checkpoint76348ddb, TP2,4slots,MTP3,chunk4096,CP-off,reserve4 and T1/.95 remain
identical. The only scheduler treatment is balanced to latency. No rebuild.

The corrected lifecycle checker from commitf1b57b2 must be staged atomically on
both nodes before starting. The supervisor remains unchanged from the completed
balanced control. It records actual native exits; the checker requires an
explicitly requested head shutdown and actual exit0/no forced kill on both ranks.
A worker may exit through coordinated drain before receiving local SIGTERM.

Exa rechecked the [native CLI contract](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/cli-design.md)
and [telemetry/shutdown semantics](https://github.com/NVIDIA/flare-local-inference/blob/refs/heads/main/helios/README.md).
The duration estimator uses fresh replay observations and can refresh stale
costs; reported GPU durations are max-rank intervals. Preserve the cold workload,
warmup and repetitions instead of changing controls to hide discovery variance.
Pinned Flare policy, vLLM budgets, exllamav3 shared chunks, TensorFold remaining
work and FlashInfer trace ownership were rechecked. No additional tuning is
combined with the existing latency patch.

## Window and gates

Use runtime local directory `latency-window-20261116T024000Z`. Snapshot both
ledgers, scripts, native/core identities, incumbent image and enabled unit states.
Arm `b12x-flare-latency-restore-20261116T024000Z.timer` for180minutes before
stopping B12X. Its helper stops the exact probe, mixed, bench, lifecycle and
memory-watch units with this window suffix before the existing restoration
helper. Disarm the incumbent watchdog, stop through its unit and require the
unchanged two-node90GiB-free/100GiB-available idle gate.

1. Append artifact406f7d03, latency policy and head-only trace
   `latency-20261116t024000z.jsonl`; worker trace remains off. Verify actual native
   executable/argv and core before measuring. Enforce1.5GiB free/8GiB available
   per node. Run the same one-repetition four-request131072-token probe,
   seed20261115, max1 output, plus its two200-token diagnostic decode rows.
2. Stop the observer and ranks, retaining invocation-bound native exits. Validate
   complete contiguous histories, no drops/truncation, exact matching hashes and
  524288 total prompt tokens. Confirm completion order changes as intended.
   Diagnostic timings cannot satisfy the untraced performance gate.
3. Append trace off, restart fresh, verify identities and run7-check API smoke.
   Run `flare_mixed_bench.py` with run-id `scheduler-latency-20261116`, then compare
   every75 request/9 case to the retained balanced control using the strict
   comparator. Preserve docs/18's separated2% rejection and overlapping-median
   investigation rules, including decoder throughput and delivery-gap tails.
4. Run the full frozen three-repetition84-row matrix (8k..128k,c1/2/4/8,
  200-token prose/code decode), matching315 request hashes to retained B12X.
   Use `flare_compare.py`; aggregate throughput cannot mask per-request TTFT.
5. After clients and enforcing monitor stop, run loaded graceful shutdown with
   the active fallback timer and corrected checker. Peer loss and the remaining
   numerical/retrieval/capacity gates stay required before adoption.

On failure, memory violation, corrupt output, rank failure or deadline, restore
B12X using the pre-armed helper. Verify both original images, health200, fresh
smoke5/5 and watchdog/tailnet before disarming fallback. Append
upstream/balanced/trace-off rollback selection. No boot changes or adoption until
all existing requirements are satisfied; the user's adoption authorization persists.

## Native diagnostic result

The latency trace completed with exact matching request hashes and524288 total
prompt tokens, zero dropped updates/truncation and contiguous complete histories.
Prompt completions occurred at131072/262144/393216/524288 cohort tokens, versus
520576/521472/522240/524288 in balanced. Sorted client TTFT changed from
233.52/234.21/234.88/235.96s to59.86/118.81/178.45/236.87s. Mean diagnostic TTFT
decreased36.71%, with approximately unchanged last completion. This confirms
the intended completion order; it is not the untraced performance verdict.
All61 memory samples passed. Both actual native children exited0 without forced
kill, with matching invocation identities; this was idle shutdown after the
probe, not the loaded-shutdown gate. Receipts are `latency-*` under the existing
qualification directory, including raw trace, client rows and comparison.

The fresh trace-off restart verifies the same executable and latency argv on
both ranks. API smoke passed7/7, and the matched75-request mixed client is live.
The restoration deadline remains05:41:30 UTC. The full84-row performance gate,
loaded lifecycle and broader production requirements remain open.
