# 65 — Decode TPS regression resolved by a full AC power cycle

**Date:** 2026-11-18 · **Scope:** both nodes · **Engine:** native Flare production (`b12x-flare-production.service`)
**Host:** kernel `7.0.0-1025-nvidia`, driver `580.178.04`, EC 3.13.7, SoC 2.158.15, USB-PD 0.5.25, ConnectX-7 28.50.1002

## Symptom

Decode throughput roughly halved on an otherwise healthy serving stack. Measured with
`scripts/decode_bench.py` (200-token outputs, three reps, idle server):

| c | 2026-11-17, warm-rebooted node | 2026-11-18, after AC power cycle | Δ |
| --- | --- | --- | --- |
| 1 | 30.50 tok/s | **43.04** | **+41%** |
| 2 | 57.34 | 83.73 | +46% |
| 4 | 60.74 | 101.10 | +66% |
| 8 | 78.25 | 99.05 | +27% |

The 2026-11-08 vLLM-B12X reference for c=1 was 40.79, so the post-cycle state is 5.5% above a
baseline measured on the older 6.17 kernel. Receipts:
`receipts/decode-flare-20261117T234958Z.json` (degraded) and
`receipts/decode-flare-20261118T100526Z-postac.json` (restored).

## What was ruled out by measurement

- **Speculative acceptance** — healthy throughout: mean acceptance length 3.04–3.08, draft
  acceptance 68–70%. Since `tok/s = steps/s × accepted-per-step`, the loss was step time, not drafting.
- **Fabric** — RDMA 108.24 / 105.45 Gb/s on the two rails; PCIe Gen5 (`126.028 Gb/s`, 32 GT/s x4).
- **Clocks/throttling** — SM 2496 of 3003 MHz, no active `Clocks Event Reason`, no thermal or power
  cap at sample time, and the `insufficient power (27W)` message absent entirely.
- **CMA reservation** — `CmaTotal` is `0 kB` on 7.0 (kernel config `CONFIG_CMA_SIZE_MBYTES=0`), the
  condition behind the widely cited `cma=128M` fix. **It was not the cause here:** throughput was fully
  restored with `CmaTotal` still `0 kB` and no `cma=` on the command line. No GRUB change was made.
- **Kernel/driver regression** — not implicated: the same 7.0.0-1025 / 580.178.04 stack now exceeds
  the 6.17-era c=1 baseline.

## Cause and fix

The degradation matched [dgx-spark-playbooks#127](https://github.com/NVIDIA/dgx-spark-playbooks/issues/127):
throughput degrades over uptime and **survives warm reboots**; only removing AC power restores it.
The cluster had been warm-rebooted repeatedly since the 2026-11-14 firmware window. A full power-off
(power brick unplugged, power button held, 60 s wait) restored throughput.

**Operational rule:** when decode TPS drops with healthy acceptance, clock and fabric, run the AC
power cycle before changing kernel, driver or serving configuration.

## Two measurement traps hit while diagnosing

1. **Never benchmark into a starting server.** `flare_production.py` runs a post-start smoke whose
   `cancel_and_recover` check requires an idle server. Concurrency applied during that window fails
   the check, the owner exits non-zero, `ExecStopPost` tears down both ranks, and the benchmark then
   records `Connection refused` zeros that look like a crash. Wait for `ActiveState=active`, not
   `activating`.
2. **Never quote a latency figure taken while another benchmark is running.** An earlier reading of
   2 tok/s was contention from a 4–8-way prefill matrix, not a regression.

## Related finding: the capacity gate sits inside allocator variance

Boot KV-pool draws observed on this pair, against the approved **2,300,000** floor:

| Boot | Tokens | Gate |
| --- | --- | --- |
| 2026-11-16 | 2,347,264 | pass |
| 2026-11-17 | 2,263,808 | fail |
| 2026-11-17 | 2,287,616 | fail |
| 2026-11-17 | 2,375,168 | pass |
| 2026-11-18 | 2,287,616 | fail |
| 2026-11-18 | 2,386,944 | pass |
| 2026-11-18 | 2,371,072 | pass |

The spread is ~2.26–2.39 M, so the floor rejects a substantial fraction of otherwise valid boots.
Two mitigations, tracked separately from this note:

- bounded automatic retry of a validated shortfall (PR #4);
- flush the page cache before each start (`sync; echo 3 > /proc/sys/vm/drop_caches`, the kit's own
  MEM-4) to reduce the variance that trips the gate. The flush belongs **before** a start; doing it
  after one changes nothing.
