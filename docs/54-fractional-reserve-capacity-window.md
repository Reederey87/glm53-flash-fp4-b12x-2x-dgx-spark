# Fractional reserve and concurrent million-token admission

Docs/35 prepares fractional reserve parsing. The current4GiB runtime starts
below the required2,350,210-token pool. This next independent serving experiment
will compare4 against3.875GiB, a128MiB reserve reduction, with the selected
scheduler/core/quantization/TP2/four slots/MTP3/chunk4096/CP-off unchanged.
It must follow performance resolution and independently closed numerical windows;
it cannot run concurrently with the ABBA or component work.

Exa MCP re-read [native memory sizing](https://github.com/NVIDIA/flare-local-inference/blob/main/helios/src/runtime_core/memory.rs),
[API/capacity metrics](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/api.md)
and [NVIDIA unified-memory guidance](https://docs.nvidia.com/dgx/dgx-spark/known-issues.html).
Native sizing uses observed host availability, driver bookkeeping, host-service
allowance and system share alongside the explicit reserve. A fixed reserve does
not guarantee identical capacity across starts. Local review of vLLM's explicit
KV-budget profiling, exllamav3's fractional per-device reserve and TensorFold's
complete prompt/reply budget supports measured admission with unchanged memory
floors. No kernel/driver, global cache drop, quantization or KV-format change.

Before executing, freeze the window controller and exact new wrapper/candidate
hashes, snapshot both old files and ledgers, and arm a restore that also restores
the old wrapper files. Both arms use the same newly frozen wrapper. Atomically
stage only while native ranks are stopped. The independent variable is the
reserve value, appended to both ledgers; never edit earlier assignments.

## Registered workload and decision

On each fresh arm verify actual native argv/core/binary, run all seven API smoke
checks, and retain the reported page/token geometry. The baseline's known pool
shortfall is recorded; the3.875GiB arm must satisfy the unchanged production floor
both before and after stress. Never reduce the reserve again in this window.

`scripts/flare_capacity_stress.py` issues two unique exact1,000,000-token prompts
concurrently, with64 generated tokens each, T1/top-p.95 and explicit ignore-EOS.
Use the same run identity/bodies on both fresh starts. Require zero cached tokens,
observed active-request count at least2, complete streams and exact output counts,
valid per-run speculative deltas, and eventual drain of active/inflight/retiring
slots. Retain actual timings and hashes without presenting them as retrieval
accuracy or a throughput comparison. These prompts test concurrent admission and
memory; docs/53 and the separate retrieval corpus test useful answers.

Keep the90GiB-free/100GiB-available idle gate at each transition and a continuous
notifying1.5GiB-free/8GiB-available serving guard. A short pool on the candidate,
memory/identity/API/client/exit failure or deadline restores B12X and old wrapper
bytes. The window controller must place the client under an external timeout:
Python HTTP/read timeouts alone do not bound a thread that keeps receiving bytes.
Require both native exits0 without forced kill. Independently verify original
B12X images, API/watchdog/tailnet and fresh5/5 before fallback disarm.

A successful capacity window permits later testing at that frozen reserve; it
does not adopt production or replace the full speed, numerical, semantic and
state gates. Every subsequent startup, reboot and watchdog recovery must again
pass the production capacity validator. A stronger long-term sizing solution
would explicitly reserve the required physical pool after accounting for peak
host allocations; it needs a separate native-memory change and qualification.

Status: stress client prepared locally. Two focused tests reject unobserved
concurrency, short/cached work and invalid metrics. Window controller, exact
wrapper freeze/staging and hardware execution remain pending.
