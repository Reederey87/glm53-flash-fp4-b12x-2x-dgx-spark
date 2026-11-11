# Process duplication: source hypothesis only

Fresh Exa lookup of the official
[vLLM multiprocessing design](https://docs.vllm.ai/en/stable/design/multiprocessing/)
identifies fork/spawn tradeoffs and CUDA/thread hazards. That document explicitly
describes historical code; it cannot establish the installed engine's contract.
No memory saving, functional compatibility or deployment clearance is claimed.

The exact image's CLI api_utils.cli_env_setup chooses spawn only if the
environment does not select a method. Its system_utils.get_mp_context calls
_maybe_force_spawn, overriding to spawn for initialized CUDA, Ray and NUMA.
Engine creation and local worker creation both use that context. Installed
set_multiprocessing_worker_envs sizes the OpenMP pool before workers start and
documents a deadlock if a parent executes a parallel region before forking.
Thus merely replacing the recipe's explicit spawn with fork is insufficient
evidence of a safe memory optimization. Forkserver is not an accepted method
in the current local vLLM environment declaration (spawn/fork only).

Local vLLM and the extracted installed source were compared after Exa. The
earlier EXL3/Flare/TensorFold/FlashInfer lifetime review provides no permission
to inherit initialized CUDA or threaded compiler state. A fresh source-guided
CPU import-sharing experiment would need the actual parent imports and process
topology, total PSS across the process group, and no synthetic memory fixture.
Any subsequent native experiment must verify parent CUDA/thread state and
child allocation, collective and graph behavior. Neither experiment has run.

The more direct next measurement is distinct selected native-owner attribution
before KV allocation. The saved post-profile/pinned-return receipts recorded
20.52/21.37GiB available on head/worker; roughly10GiB was a minimum during an
earlier postload phase, not this boundary. Future admission must check fresh
availability, not assume either historical value. The stopped model's228 tuple
counts cannot identify those instances.
Do not re-enter the unsafe post-capture boundary just to inventory them.

Installed source hashes are retained in
`receipts/cute-artifact-audit/multiprocess-source.sha256`; source bytes stay local.
No launch environment, process method, checkpoint, KV pool or serving behavior
was changed by this read-only source audit.
