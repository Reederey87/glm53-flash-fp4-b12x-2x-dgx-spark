# Pre-registered Flare export and native-start gate

The engine treatment and frozen controls remain those in `08-flare-build-window.md`.
This gate is written before export or any native candidate measurement.

Prerequisites: both build units succeed, both CUDA probe receipts pass, source
and lock hashes match, no incumbent container runs, and both hosts pass the
90 GiB free / 100 GiB available memory gate. Keep the private runtime snapshots,
previous image identities, explicit candidate config and matching coordination
token. Keep the head's private signing key local; transfer only its public profile.

Start `b12x-flare-prepare@0.service` on the head. It starts rank 1's preparation
unit, exports under the isolated candidate cache and stops its peer on exit.
Export deadline: 90 minutes. Retain ordinary and speculative graphs. A binding,
nonfinite, memory, signature or transport failure fails this phase; do not weaken
upstream checks or alter the checkpoint to pass it.

Record the exported primary hash and verified metadata, graph catalog, native
binary hashes, public signing fingerprint and capacity inventory. Accept only
that locally generated fingerprint under `local-development`, storing the exact
profile and primary hashes in private `local/accepted-core.json` on both nodes.
Start `b12x-flare@0.service`; it coordinates the worker's unit. Health must return
200 within 900 seconds; model ID must be the NVIDIA checkpoint's ID and reported
context at least 1,000,000. Run `flare_smoke.py` in the locked preparation
environment: native prompt tokens must match the pinned tokenizer for omitted
effort=Max and explicit low/high/max; tools, structured output, observed prefix
reuse, and cancellation followed by generation must pass.

Run upstream exported-core retrieval regression at concurrency 4 and 8, cold and
cached, retaining full receipts. Any corrupt output or INVALID_SPECULATION fails
correctness. A four-slot/MTP-3 export does not test the >16-query-row graph route;
its separate SM121 regression and KDA numerical qualification remain necessary
before adoption. Do not count a skipped qualification-only native test as passing.

Performance collection uses `flare_bench.py` with the same checkpoint tokenizer,
seed, prompts, budgets and sampling on both engines: **temperature 1, top-p .95**.
the Flare core does not preserve greedy temperature-zero semantics; the earlier greedy incumbent smoke is a health
reference and is not a fair performance comparator. Exact raw-token prefill at
8192/16384/32768/65536/131072 runs at c1/2/4/8; every request must report its exact
length and zero cached tokens. Record actual decode lengths, per-request TTFT and
decode throughput, aggregate throughput, and per-run speculative counter deltas.
Default three repetitions; extend to five if noisy. A repeated >2% regression
in comparable throughput/acceptance fails the preservation-of-speed requirement.
Do not infer usable capacity from incompatible KV accounting: quantify physical
storage, logical capacity and actual long-context admission separately.

No automatic adoption: after failure, inconclusive results, or a passing trial,
stop both candidate ranks and restore B12X through `flare_restore.sh`, verify
health/functional smoke, and restore its watchdog. A phase's timed rollback must
remain armed throughout, with its deadline recorded before starting that phase.
Candidate API remains loopback port 8001; tailnet routing remains on B12X.

Basis: [upstream API](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/api.md),
[exported-indexer defect and regression](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/glm-batched-speculation-defect.md),
[upstream numerical TODO](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/TODO.txt).
Pinned local source is authoritative where indexed web text differs.
