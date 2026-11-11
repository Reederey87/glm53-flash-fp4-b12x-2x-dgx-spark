# Pinned return passed; later startup safety failed

Both actual-model native calls returned536,870,925 known-idle pinned bytes
(512MiB plus13bytes). Active150,996,524bytes, CUDAallocated/reserved, fraction1.0,
host allocation count and original17GiB admission stayed unchanged. Four host
blocks freed per rank. Actual available-memory gain544,346,112bytes head and
538,435,584bytes worker. Both unchanged256MiB/128MiB gates PASS; no inferred
pending-event return. Actual provider/worker/helper/PID/trace order validate.

Both target/MTP bound scopes pass,1817trace records/rank, minima10.142/11.284GiB,
restored1.0, actual requested/resolved Humming and advertised2,350,210-token pool.
This demonstrates real reclamation, not a safe complete deployment.

Head reached1.823GiB available2026-11-11T05:10:37Z after graph capture finished
at05:10:36Z. The independent2GiB guard stopped the window before health, smoke,
parity or speed. Last observed worker minimum2.958GiB is a sampled minimum, not
proof about unsampled teardown time. No adoption or TODO3 performance verdict.

Stop-only complete05:10:43Z primary1/recovery0, both model objects absent,
canonical ledger restored and proxy/watchdog inactive. Preserve terminal output.
No lower floor, smaller17G pool or automatic recovery boot. Pinned return alone
is insufficient; next source/ownership work must target the remaining capture/
post-capture footprint rather than repeat an unmeasured flush. The negative
reported graph-memory delta is not proof that capture costs no host memory.
