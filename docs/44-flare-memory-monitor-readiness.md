# Memory monitor readiness and failure propagation

The initial docs/42 window was aborted: its restoration label contained `a16`,
which the monitor's intentionally restricted service-name parser rejected.
Type=exec reported successful process execution before that argument failure,
and the old orchestration started test ranks without checking monitor readiness.
No memory samples were recorded. Live inspection found over100GiB free on both
nodes, but that does not replace continuous qualification evidence. The run is
incomplete; its initial three layer0 cases and identity output do not qualify it.
B12X restoration was requested immediately when the missing guard was discovered.

Exa reviewed official [systemd service readiness/watchdog semantics](https://freedesktop.org/software/systemd/man/latest/systemd.service.html)
and [systemd-run](https://freedesktop.org/software/systemd/man/latest/systemd-run.html).
Type=exec confirms execve, not application initialization. Prefer native notify
readiness and watchdogs over a process-is-active poll. Local vLLM waits for explicit
engine READY messages; TensorFold distinguishes worker/watchdog liveness and
stalled work; exllamav3 invalidates generator state after errors. These reinforce
fail-closed initialization; none supplies a model numerical pass.

The monitor sends READY=1 only after its first valid two-node observation is
flushed, followed by WATCHDOG=1 after each healthy sample. Observation errors or
memory violations keep the existing immediate restoration path. New GPU windows
use Type=notify, NotifyAccess=all (Python can be uv's child),30-second startup
and watchdog limits, LimitCORE=0 and OnFailure naming the pre-armed restoration
service. A parser failure, crash or heartbeat stall therefore prevents launch
or independently restores B12X. Normal intentional monitor stop is not failure.
No memory threshold, serving source, precision or driver changes. Legacy use
without NOTIFY_SOCKET retains its existing behavior.

The83-test local suite passes, including real Unix-datagram readiness/heartbeat
checks, invalid observations suppressing notifications and visible socket errors.
The sandbox-only socket bind was denied; the same suite passed with normal local
socket access. CPU-only `memory-notify-probe-20261116T140000Z` must also pass:
synthetic healthy observations demonstrate readiness and a later heartbeat;
invalid arguments must fail startup and invoke a receipt-only fallback; an
intentional heartbeat stall must yield systemd Result=watchdog and invoke its
separate receipt-only fallback. These probes never use GPUs or production units;
all probe timers/units are stopped after retained terminal results.

Register retry `layer-native-window-20261116T150000Z` only after the aborted
layer-a16 window independently restores B12X and closes, and the CPU probe passes.
Use alphabetic labels compatible with the existing parser. Numerical scripts,
all nine cases and bounds remain exactly those frozen in docs/42. Both-node source
manifests now include the notify-capable monitor. Keep90-minute fallback and all
existing memory/termination limits. Full-target docs/43 now requires this retry's
9/9 pass and closure and uses the same verified notify/watchdog protection.
