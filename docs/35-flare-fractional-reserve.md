# Fractional reserve support — local, not applied

The latest observed pools remain below the 2,350,210-token production floor.
Flare's native CLI accepts fractional binary sizes, but this kit accepted only
integer reserves. The local launcher now accepts finite decimal GiB values at
least1, preserves last-assignment rollback and normalizes4.0 back to4. Both rank
argv receive the same explicit reserve; preparation settings and exported core
remain unchanged. The runtime still uses its frozen wrapper and4GiB reserve.

Exa reviewed [runtime memory limits](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/cli-design.md)
and [cache sizing](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/model-preparation.md).
Pinned native `runtime_core/limits.rs` accepts fractional sizes; `memory.rs`
reconciles observed loading and uses integrated host availability, mandatory
headroom, host allowances and a system share. An explicit runtime reserve replaces
rather than adds to the exported reserve. Source review also covered vLLM's
explicit KV budget, exllamav3 fractional per-device reserve and TensorFold's
projected concurrent-stream budget. Those are design evidence, not proof of safe
capacity on these two nodes.

A future independent window can compare4 versus3.875GiB, a128MiB step. Do not
stage this while the scheduler diagnostic is active. Freeze the new wrapper on
both nodes before the window, retain the old wrapper and accepted core hashes,
and preregister the full capacity/load gate before starting. Keep the existing
1.5GiB MemFree/8GiB MemAvailable serving floor and production capacity minimum.
If either fails, restore; do not reduce reserves again within that window.
Observed capacity varies per startup, so even a successful warm start does not
replace boot and watchdog-recovery qualification. No memory watermark, driver,
kernel, quantization or KV storage format change is proposed.

All79 local launcher/client tests pass, including decimal forwarding to both
ranks, unchanged export commands, last-wins rollback and malformed/nonfinite
value rejection. No hardware capacity improvement is claimed.
