# Selected-layer A16 scale audit — 2026-11-16 UTC

> Historical architecture or qualification record. Current production, unresolved gates and the research pause: [docs/63](63-production-pause-checkpoint.md). Old window controllers must be adapted before reuse.

All 288 experts in target layers 3, 24 and 44 were decoded on the CPU and partitioned for both TP2 ranks. Across 1,358,954,496 block scales, none fall below the packed A16 boundary. Each W13/W2 population has maximum 448 and lifting factor 1. This clears this particular scale-discard condition for the scanned layers only; 39 target layers, MTP packing and native arithmetic/replay remain unqualified.

| Layer | TP rank | Projection | Scale count | Minimum nonzero E4M3 byte | Below boundary |
| --- | --- | --- | ---: | ---: | ---: |
| 3 | 0 | w13 | 150,994,944 | 90 | 0 |
| 3 | 0 | w2 | 75,497,472 | 90 | 0 |
| 3 | 1 | w13 | 150,994,944 | 90 | 0 |
| 3 | 1 | w2 | 75,497,472 | 92 | 0 |
| 24 | 0 | w13 | 150,994,944 | 91 | 0 |
| 24 | 0 | w2 | 75,497,472 | 92 | 0 |
| 24 | 1 | w13 | 150,994,944 | 91 | 0 |
| 24 | 1 | w2 | 75,497,472 | 90 | 0 |
| 44 | 0 | w13 | 150,994,944 | 66 | 0 |
| 44 | 0 | w2 | 75,497,472 | 49 | 0 |
| 44 | 1 | w13 | 150,994,944 | 68 | 0 |
| 44 | 1 | w2 | 75,497,472 | 49 | 0 |

The independent pinned CSF decoder read 737,998,026 bytes of scale payloads. The receipt hashes every scanned tensor name, shape, dtype and payload, and all shard headers. Both rank-local populations use all experts before choosing the lifting factor; a selected-expert maximum was not substituted. CUDA initialization was checked and remained false. The exact audit script hash is in the window receipt.

The audit ran from 00:27:05 to 00:31:01 UTC, with 232.43 CPU seconds, a 2.51 GiB recorded memory peak and zero recorded swap peak. Both nodes first passed 115 GiB free / 114 GiB available. Runtime manifests, the head native core, accepted-core files, launchers and native binaries remained unchanged. No checkpoint, kernel, reserve, driver or system configuration was changed.

The transient audit unit was collected after completion, so the later systemctl snapshot contains defaults rather than retained exit status. The complete audit output and durable invocation/resource journal are the evidence used here. Future audit units retain their completion state until it is captured; this follows the [official systemd-run contract](https://freedesktop.org/software/systemd/man/latest/systemd-run.html).

B12X restoration began immediately after collection and hash verification. Original images on both nodes, health 200, watchdog and tailnet were verified at 00:37:31 UTC. The retained smoke unit then reported code=exited/status=0 and all five checks passed; the restoration timer was disarmed at 00:38:07 UTC. No adoption follows from this selected-layer audit.

This gate follows the [source-level precision review](10-flare-precision-audit.md). Exa located the [related Marlin report](https://github.com/sgl-project/sglang/issues/48906) and [rescaling implementation](https://github.com/vllm-project/vllm/pull/34577); pinned FlashInfer A16 preparation confirms that the full expert population sets the factor. The related MXFP4/E8M0 issue is a different format and is not evidence of a failure in this NVFP4/E4M3 checkpoint.

- [All scanned populations and histograms](../receipts/flare-qualification-20261115/scale-audit-layers-3-24-44.jsonl)
- [Window identity, hashes and resource evidence](../receipts/flare-qualification-20261115/scale-audit-window.json)
- [Collected transient-unit snapshot; see limitation above](../receipts/flare-qualification-20261115/scale-audit-terminal.txt)

- [Restored identities, services and retained smoke exit](../receipts/flare-qualification-20261115/scale-audit-restored-runtime.txt)
- [Fresh B12X functional smoke](../receipts/flare-qualification-20261115/scale-audit-restored-smoke.txt)
