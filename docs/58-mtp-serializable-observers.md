# Serializable MTP qualification observations

The production-capture attempt failed before numerical replay on both ranks:
Flare replaces local closures with unavailable process-local resources in the
compiler worker. Both first cases exited1 after approximately22.7seconds.
Retain the original logs/XML under`mtp-replay-aot-*`. Independent B12X recovery,
original images, API/watchdog/tailnet and fresh5/5 passed10:12:07 UTC; fallback
closed. Restore273cb5859fc4483daa05d3510a7e0d9e and smoke
a2c7db5223cd4957a0c82d05e7b6791a both ended with actual exit0/PID0.

Exa fetched NVIDIA's [forward metadata serializer](https://github.com/NVIDIA/flare-local-inference/blob/main/ignition/preparation/forward_metadata.py).
The pinned local serializer explicitly substitutes local functions/lambdas and
local classes; its AOT tests instead use importable callable owners. Reviewed
vLLM's serialized compiled artifacts, exllamav3's metadata/resource ownership,
TensorFold's callable GLM MTP composition and FlashInfer's unchanged normalization
boundary. Reusing the production serializer and importable observers is narrower
than cloud-pickling CUDA resources, changing compiler policy or eager fallback.

`mtp_replay_forward.py` moves only the five observer kinds and composed forward
to module-level callable classes. The sparse-selection observer preserves the
same dataclass field copies; the existing matched-selection reference is unchanged.
The entire numerical replay body from random input generation onward remains
byte-identical. Model arithmetic, metadata/state, capacities, bounds, completion
fences and allocation assertions are unchanged. No serving code changes.

A CPU-only integration preflight runs the actual pinned serializer in a fresh
child process on each Spark. Both passes call all deserialized observers, exercise
both cache branches, preserve shared aliases and the indexer's bound-method cycle,
and verify CUDA was never initialized. This uses synthetic operations and does
not claim real model capture or numerical correctness.

## Frozen retry

`mtp-replay-serial-window-20261117T050000Z` requires independent recovery and
fallback closure of the intervening docs/55 scheduling diagnostic. Both source
manifests and CPU serialization preflights must pass before stopping B12X.
Run the unchanged five cases per rank in fresh processes. Preserve original
memory floors, bounded controller/rank durations, notifying guard,90-minute
fallback and independent original-image/fresh5 recovery. A failing or incomplete
case never counts as a numerical pass. The retry is prepared but unrun.

Capacity still requires a successful MTP gate and the unresolved performance
gate. The scheduling diagnosis does not depend on this mathematical fixture.

The preflight additionally requires two complete CPU Dynamo traces of its
synthetic observer composition (one per cache branch), with real CPU output
checks after capture. This is a tracing test, not GPU AOT/code-generation evidence
or a serving fallback. The expanded preflight is frozen locally and must pass
on both nodes before the GPU retry; it has not yet been executed.
