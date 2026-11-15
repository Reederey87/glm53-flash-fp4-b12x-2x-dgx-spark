# Native activation component result — 2026-11-15

Kit `6bf1900`, run `20261115T220113Z-723169`: **49 passed, zero skipped**.

| Suite | Passed |
| --- | ---: |
| Checkpoint weights/scales | 12 |
| Native indexer replay | 4 |
| Learned KDA prefix/continuation | 2 |
| State transfer | 31 |

The independent variable was native dense activations in the KDA preparation
session. Original TP2/width4 and TP4/width6 errors .03793176 and .02955953 became
**0.0**; all later original assertions passed. Tuning selected quantized mode
for blockscaled input/output projections at both row counts, preserving BF16
partitions. TP4 is a rank-local geometry control, not a four-node test.

[Scalar results, projection configurations and XML hashes](numerical-native-activation-window.json)
retain the exact evidence. No bounds changed. The original failures remain.
This result does not establish full-model accuracy or performance; the old
serving core still uses auto precision and has not been replaced.

B12X restored health200 at 22:09:00 UTC. Smoke5/5, original image hashes on both
nodes, watchdog and tailnet verified at 22:10:03; safety timer disarmed.
