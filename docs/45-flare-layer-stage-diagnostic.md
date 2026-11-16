# Deployed-mode attention-stage mismatch

> Historical architecture or qualification record. Current production, unresolved gates and the research pause: [docs/63](63-production-pause-checkpoint.md). Old window controllers must be adapted before reuse.

The docs/44 protected retry completed five cases on each rank, then failed
layer3/prefill4096 at the exact attention-stage assertion. Both ranks report
5,954,429/16,777,216 differing elements (35.5%), maximum absolute difference
0.001953125. Persistent state and cross-rank output/routing assertions preceding
this comparison passed. This is a numerical gate failure, not a qualified arm.
The69 memory samples were healthy. Both pytest processes exited1. Independent
B12X restoration and fresh5/5 smoke completed07:11:54 UTC and fallback disarmed.
Receipts use `layer-native-failed-*`.

Exa MCP reviewed upstream [MTP numerical contracts](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/mtp-design.md),
[core design](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/core-design.md),
[open numerical work](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/TODO.txt),
and [preparation controls](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/cli-design.md).
They require same-operand comparisons and measured repeatability for varying
reduction order. A stronger option is an operand-level independent reference;
whole-model output similarity cannot close an unexplained component mismatch.
The pinned `QuantizedProjection` already disallows BF16 atomic reduction for
MXFP8 weights by default, so applying that policy is not an identified fix.
Reviewed local Flare linear/MLA code, FlashInfer GEMM reduction policy, vLLM
FlashInfer quantization adapter, exllamav3 linear implementation and TensorFold's
kernel contract. TensorFold's separate repeatability/input-ownership checks
inform this diagnostic; no server or kernel substitution is proposed.

## Frozen diagnostic before further code treatment

Window `layer-stage-window-20261116T160000Z` repeats only the failed case with
exactly the deployed A16 owner/calibrated A4 prefill and native dense activation.
After the original replay, but before its assertions, collect nine observations:
eager/graph/native/native/eager/graph/graph/native/eager. Reset identical persistent
state each time. Python graph and native replay use the same captured graph;
no instrumentation is inserted inside capture. Retain original eager/native
comparisons, each stage's exact hashes and finite/mismatch counts, original
output-bound comparisons, same-path repeatability, cross-rank stage hashes,
source immutability and state repeatability. Restore the original observed
buffers/state before running every original assertion. Full upstream-method
AST comparison allows only documented host/deployed-mode adaptation and this
post-replay diagnostic. No bound is widened. An expected pytest1 remains1.

Completion requires nine observations on both ranks, actual terminal codes0/1,
all memory samples healthy and unchanged runtime hashes. It means evidence
collection only. The guard requires first-sample readiness,30-second watchdog
and restore on failure. Retain90-minute fallback,4500-second controller and
3900-second rank bounds, GPU locks and existing memory floors. Only start after
verified prior B12X closure. Independently verify B12X restoration, fresh5/5,
both original images, API/watchdog/tailnet and no test/native PIDs before
fallback disarm. Do not run the full-target gate until the layer failure closes.
