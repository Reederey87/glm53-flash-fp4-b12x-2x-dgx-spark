# Incumbent baseline vs b12x kit

Same pair, same image digest, same checkpoint, same flags. The only change is
the runtime tree/contract. Both runs are cache-cold, 200-token decode, identical
requested lengths.

| metric | incumbent (`speed-20261108T133210Z`) | b12x kit (`speed-20261108T135615Z`) | Δ |
|---|---:|---:|---:|
| prefill 8k tok/s | 2243.9 | 2204.1 | −1.8% |
| prefill 16k tok/s | 2279.5 | 2284.3 | +0.2% |
| prefill 32k tok/s | 2290.0 | 2289.6 | 0.0% |
| prefill 64k tok/s | 2297.4 | 2308.8 | +0.5% |
| prefill 128k tok/s | 2271.7 | 2261.2 | −0.5% |
| decode c1 tok/s | 27.32 | 27.80 | +1.8% |
| decode c2 tok/s | 41.10 | 41.74 | +1.6% |
| decode c4 tok/s | 61.35 | 59.18 | −3.5% |
| decode c8 tok/s | 58.79 | 58.64 | −0.3% |
| accept len c1/c2/c4/c8 | 2.29/2.47/2.58/2.48 | 2.49/2.57/2.51/2.57 | + |
| accept rate c1/c2/c4/c8 | 0.257/0.294/0.317/0.295 | 0.297/0.314/0.302/0.314 | + |

Read: prefill is at parity (±2%); decode c1/c2 are slightly higher, c4 lower by
3.5%, c8 flat. Single runs cannot separate those small differences from
run-to-run variance. The c4 point is a watch item, not dismissed and not a
reason to revert: the gate is absolute and passes, and no treatment touched
scheduling.

Provenance notes:
- `speed-20261108T132150Z`: valid cache-cold baseline, predates the acceptance
  counter fix — acceptance `null`, not used.
- `speed-20261108T133053Z`: cache-hit artifact (deterministically seeded
  prompts); prefill rows of 133k–485k tok/s are not evidence.
- `speed-20261108T133210Z`: clean baseline used above.
- `speed-20261108T134216Z`: first post-swap run (pre-hardening script).
- `speed-20261108T135615Z`: post-swap run from the current script, enforces the
  exact ladder and rejects cache hits; used above.
- Prompts are not stored. Percentages are exact for the recorded runs; the
  variance statement is qualitative.
