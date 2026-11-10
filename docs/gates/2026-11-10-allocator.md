# Candidate 2 — allocator headroom (pre-registered 2026-11-10)

## Frontend integration repair before retry

The first B dispatch never booted an engine: the pinned upstream validator
rejects duplicate env keys, including the required appended rollback. A scoped
runtime ENV_FILE override restores the hash-verified original control backup.
The ledger remains unchanged. Code `90c92da` derives an atomic mode0600
last-wins upstream config, preserving the original assignments and ledger;
it also discards failed Docker-inspect stdout when confirming absent ranks.
Exa checked the primary [upstream launcher](https://github.com/eugr/spark-vllm-docker/blob/main/launch-cluster.sh)
and [Docker inspect contract](https://docs.docker.com/reference/cli/docker/inspect/).
No upstream checkout was patched. Literal, single-line assignments are the
supported ledger format, matching the pinned upstream validator.

Astra review cleared this next B experiment conditionally: run actual pinned
validator and full frontend dry-runs for B and appended rollback A; remove the
temporary ENV_FILE override and verify effective config; clear the start-limit
counter once before the retry; refresh hashes including `render_env.sh`;
serialize render/start calls sharing `local/upstream.env`; verify both ranks'
image, argv and allocator environment before measurement. No adoption approval.
This repairs configuration handoff only; the experimental variable remains the
allocator, with the same image/checkpoint, 17G KV and scheduler controls.

Additional user requirement (2026-11-10, before B was started): an Astra
sub-agent performs final code review before deploying the next candidate.
The waiting switch driver was stopped/cancelled before any B env append;
control measurement continues. Resolve review blockers and review the final
bytes before authorizing the next switch. Apply this requirement to subsequent
candidate windows too.

Review remediation before B: require complete, successful control and strict
per-request decode evidence; observer initial readiness plus ongoing heartbeat
checks; TERM/INT handling and a separate ExecStopPost recovery hook; separate
primary/recovery status; verify both rollback images/allocator variables and
reopen external traffic only after 5/5 smoke and health200. The original control
prefill code/budgets remain unchanged. Preserve its original full receipt and
repeat the twelve control decode batches with per-request usage/DONE/timing
validation before B. Repeat the same twelve batches **after B's full ladder**
too, preserving both initial receipts and their hashes; compare post-ladder
decode in both arms, never A post-ladder against B interleaved. The changed
decode validation/recording is identical in both compared arms; historical
aggregate-only decode rows are excluded. Preserve all raw counter snapshots
and require observed finite samples and unchanged API/engine/rank host PIDs
across every measured decode batch.

Safety research additionally checked the primary
[systemd service](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)
and [kill-mode](https://www.freedesktop.org/software/systemd/man/latest/systemd.kill.html)
contracts and [vLLM streaming usage](https://docs.vllm.ai/en/latest/features/per_request_metrics/).
CPU-only failure injection must cover lost usage/DONE, reset counters, malformed
or failed memory probes and interrupted window recovery before B is released.
Readiness must match the current observer InvocationID with heartbeat age in
0..20 s, including for A. Assert watchdog timer/service and external proxy are
inactive before B. Recovery failures must actually close the proxy, including
partial start or post-start receipt failure; verify each unit independently.

Arm A: image allocator default (no override), 17 GiB KV. Arm B: only
`PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` on both ranks, same KV.
`B12X_ALLOCATOR_CONF` is an optional launcher passthrough recorded in the
append-only runtime `.env`. Empty restores the default. No image build.

Frozen: image `3b5da79c42ed4204440cfb07c6de1eba46441d5cba6b57d5428d44e60c10d0ed`,
checkpoint `76348ddb`, TP2, MTP3/humming, four seats, 1,000,000 context,
4096 batched tokens, FP8 KV, block256, RoCEnante, driver/kernel unchanged.
Restart each arm through `vllm-b12x.service`; stop its watchdog throughout.
Save both-node env/file hashes, image identity and process argv before measuring.
Start a fixed observer for both arms; stop on <2 GiB host MemAvailable or a
failed remote probe. This is a safety abort, never evidence of performance.

Gate: health in 900 s, exact allocator env on both ranks, KV >=2,350,210,
all five functional checks PASS including tools and default Max. Run the full
8k/16k/32k/64k/128k ladder at c1/2/4/8 with exact input-token budgets, unique
first tokens (zero cache hits), one output token; queueing at the four-seat cap
is included and reported. Decode 200-token budget, three reps, same code prompt
at each concurrency; report run-delta acceptance rate and mean acceptance length.
Warm once per arm. Preserve partial results on failure.

Reject a >2% median decode regression or >2% acceptance-rate regression at
any concurrency, or >2% median prefill regression at any matched length and
concurrency; repeat noisy cells before declaring a robust regression.
Allocator is useful if minimum serving headroom improves >=1 GiB on both ranks
with no robust speed/acceptance regression. No automatic production adoption:
restore A and present receipts for approval before permanent adoption.

Only if B clears safety and speed: separately pre-register a 19 GiB KV arm,
then 20 GiB if justified. Require measured minimum headroom minus the proposed
increase >=3 GiB on BOTH nodes; never infer it from allocator reserved bytes.
Each KV increase is its own treatment/restart. Do not increase KV after an
allocator failure. Restore the original recipe/IMAGE and append
`B12X_ALLOCATOR_CONF=` on rollback; restart, smoke, re-arm watchdog, health200.

Research: NVIDIA model discussions [7](https://huggingface.co/nvidia/GLM-5.3-Flash-FP4-Local/discussions/7)
and [8](https://huggingface.co/nvidia/GLM-5.3-Flash-FP4-Local/discussions/8)
measure headroom at a smaller pool, not proof for this profile. PyTorch's
[allocator analysis](https://docs.pytorch.org/devlogs/eager/2026-06-01-cuda-caching-allocator/)
and NVIDIA's [graph memory guide](https://docs.nvidia.com/dl-cuda-graph/latest/troubleshooting/memory-issues.html)
explain fragmentation and capture limitations. vLLM
[issue55569](https://github.com/vllm-project/vllm/issues/55569) also proposes
a 64 MiB sparse-indexer budget; it is a separate treatment, not bundled here.
cudaMallocAsync and loader/workspace changes also change allocator contracts
and are deferred until this simpler comparison is measured.

Local review: `vllm/vllm/v1/worker/gpu_worker.py` explicitly skips automatic KV
sizing when bytes are pinned; FlashInfer b12x MoE has separate preparation and
execution lifetimes; Flare `ignition/recipes/glm53/bootstrap.py` reports reserved,
allocated and free independently after capture cleanup; EXL3 memory utilities
flush cached blocks; TensorFold `docs/memory-profiling.md` recommends actual
token budgets, applied-profile receipts, separate cold/concurrent runs and
phase memory measurements. Adopt that measurement technique in this harness;
do not port its engine-specific cache spill or change the quant/KV pool.
