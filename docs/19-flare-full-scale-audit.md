# Full CSF scale audit — 2026-11-16 UTC

The CPU audit completed all 42 routed-expert layers (3..44), all 288 experts,
both TP2 partitions and both W13/W2 populations. Across 19,025,362,944 scales,
none fall below the packed A16 boundary after the full-population lifting factor.
All 168 populations have maximum 448 and factor 1; the minimum nonzero E4M3 byte
over the scan is 49. This clears the scale-discard condition for these populations.
It does not qualify native packing, A4 prefill, MTP, or full-model arithmetic.

The retained unit ran from 00:40:47 to 01:34:13 UTC and exited successfully:
`LoadState=loaded`, `SubState=exited`, `MainPID=0`, `Result=success`,
`ExecMainCode=1`, `ExecMainStatus=0`. Its invocation was
`90797e75bcb44082ac2fc11e6c78c3b8`. The unit recorded 3,166.103 CPU seconds,
29,089,075,200 bytes memory peak (including charged file cache) and no swap peak.
This is retained terminal evidence, unlike the collected earlier three-layer unit.

The frozen audit script was
`62df5625b1a2ea9b6fff9d2b9c256f0d87c29d9821e4975c215a21c3f44c24e3`,
from kit 53ff17c. The independent checkpoint decoder was pinned at Flare 5a4e867
and checkpoint 76348ddb. It read 10,321,055,136 bytes of scale payloads and reported
no CUDA initialization. Its payload digest is
`7307cb22ecb1daa2cc8497bcbe9fee70023396e9547d46b06ce34b1d2f3916db`.

A separate local validation required exactly 170 JSONL records, all 168 unique
layer/rank/projection identities, the expected 150,994,944 W13 or 75,497,472 W2
counts, and complete manifest/footer coverage. It independently decoded occupied
E4M3 histogram values, rejected negative/nonfinite values, and recomputed maxima,
factors, zero counts and boundary counts. No footer-only success inference was used.
Original runtime configuration, accepted core, launcher and CLI hashes remained
unchanged on both nodes; the head core hash also matched.

## Restoration

The audit and isolated worker tests/build were terminal before restoration.
Head MemFree was 88 GiB after exit, below the existing 90 GiB startup gate. Following
an Exa review of [POSIX_FADV_DONTNEED](https://www.man7.org/linux/man-pages/man2/posix_fadvise.2.html),
only cached pages of the forty main checkpoint shards were advised away after
fsync, under the existing operation lock with all model units stopped. The files
were selected from the pinned index; resolved paths were constrained to their
verified shared Hugging Face blob locations, and inode/device/size/mtime/ctime
were unchanged. Initial conservative path/count guards refused before advising
any files; inspection established the shared blob layout and two auxiliary index
entries. Neither auxiliary file needed advice.

MemFree then reached 114 GiB. No model data was deleted, no global cache flush or
sysctl was used, and startup memory thresholds remained unchanged. B12X restoration
started through the pre-armed restoration service. At 01:44:05 UTC, both nodes
were verified on the original image, API health was 200, the retained smoke
reported exit 0 and 5/5 passes, and the watchdog/tailnet services were active.
The smoke unit was stopped and the restoration timer was then disarmed.

- [All 168 populations and histograms](../receipts/flare-qualification-20261115/scale-audit-all-layers.jsonl)
- [Independent validation](../receipts/flare-qualification-20261115/scale-audit-all-validation.json)
- [Retained terminal state](../receipts/flare-qualification-20261115/scale-audit-all-terminal.txt)
- [Head hash verification](../receipts/flare-qualification-20261115/scale-audit-all-head-hash-check.txt)
- [Worker hash verification](../receipts/flare-qualification-20261115/scale-audit-all-worker-hash-check.txt)
- [Targeted cache advice receipt](../receipts/flare-qualification-20261115/scale-audit-all-cache-release.json)

- [Restored runtime and retained smoke exit](../receipts/flare-qualification-20261115/scale-audit-all-restored-runtime.txt)
- [Fresh five-check smoke](../receipts/flare-qualification-20261115/scale-audit-all-restored-smoke.txt)
- [Timer disarmed after verification](../receipts/flare-qualification-20261115/scale-audit-all-timer-disarmed.txt)
