# Flare production ownership

The user explicitly approved provisional production on 2026-11-16 and paused
further research. The owner, watchdog, proxy, release decision and both-rank pins
are installed. Operational receipts and current status are in
[docs/63](63-production-pause-checkpoint.md). The implementation history below
retains the original qualification target; it is not evidence of completed research.

## Source evaluation

Exa review of the official [service contract](https://freedesktop.org/software/systemd/man/latest/systemd.service.html)
supports a oneshot cluster owner with RemainAfterExit: it becomes active only
after readiness and smoke complete. ExecStopPost also runs after failed startup,
so partial startup cannot leave a worker outside cleanup. The native rank units
retain Restart=no; only the head owner coordinates restart. No WatchdogSec is
configured because the native application does not provide sd_notify heartbeats.

The official [timer contract](https://freedesktop.org/software/systemd/man/latest/systemd.timer.html)
requires OnCalendar for persistent catch-up. The adoption window must install
an absolute UTC deadline with Persistent=true and AccuracySec=1s, enable it on
disk, verify the next trigger, and create production-pending.json before switching
ownership. A transient timer is insufficient for the controlled reboot.
Also include OnBootSec=2min: the pending marker records the same deadline as
`rollback_after` (Unix seconds), and the helper skips an early boot check. This
allows a later reboot to retry cleanup after a failed/previously-fired fallback.
The rollback service retries failures with a three-start/hour systemd limit;
an explicitly requested early restoration uses the helper's `--now` option.
[User lingering](https://freedesktop.org/software/systemd/man/latest/loginctl.html)
must be observed on both nodes before enabling startup; network ordering does
not establish remote SSH readiness.

After lookup, reviewed vLLM engine-manager liveness/finally shutdown,
exllamav3's explicit generator/checkpoint/pinned-buffer cleanup, TensorFold's
scheduler-owned shutdown and existing B12X bounded watchdog. These favor one
owner and verified teardown before the unchanged two-node memory gate. No
TensorFold server or checkpoint persistence is introduced by these files.

## Behavior and limits

- `b12x-flare-production.service` owns both native ranks. Startup verifies a
  separate qualification decision and exact per-rank recipe/core-state hashes,
  checks the executable provenance, waits for the peer, rejects an active B12X,
  stops stale native ranks, releases only candidate file-cache pages, and passes
  the original90GiB free/100GiB available gate. It then dispatches the worker synchronously before the head, waits for both
  ranks and HTTP health, and runs all seven API smoke checks as warmup. This
  avoids inspecting a previous worker failure before the new invocation starts.
- `b12x-flare-production-watchdog.timer` checks both native unit states and HTTP
  health. Two failed observations permit `try-restart` of an active owner only.
  A manual stop, maintenance, disabled owner, or startup transition is left
  alone. Three attempts per six hours are persisted before dispatch, including
  failed dispatches; clock rollback cannot reset that budget. A failed owner
  startup needs the guarded rollback or operator attention, not a restart loop.
  This health probe is not proof of GPU progress under every possible hang.
  File data and the containing directory are flushed around atomic replacement,
  following Exa's [Linux fsync contract](https://man7.org/linux/man-pages/man2/fsync.2.html).
- `b12x-flare-tailscale.service` exposes the existing external8000 port through
  the existing TCP proxy to native8001. Stop/disable the B12X proxy before enabling
  it; rollback restores the original proxy and startup ownership.
- `b12x-flare-production-rollback.service` is paired with the deadline-specific
  persistent timer generated at adoption. It disables Flare startup/watchdog/
  proxy, appends rollback selections on both nodes, and restores B12X through
  its original unit. Keep the pending marker until independent image/API/smoke
  verification. Never run both endpoint proxies or both GPU startup owners.

Twelve local tests exercise manual-stop behavior, healthy reset, persistent budgets,
clock rollback, corrupt ledgers, pin drift and an unqualified decision. Shell
syntax passes. Installed-path checks, real watchdog recovery, endpoint smoke
and a controlled two-node reboot subsequently passed in the approved adoption
window. Exact operational results and retained failures are recorded in docs/63.

## Startup capacity enforcement

The production readiness check now requires fresh reported pool capacity of at
least 2,350,210 tokens, with consistent positive page/token geometry. A pinned
recipe alone cannot guarantee this because native allocation uses observed host
memory. Missing, duplicate, malformed or below-floor metrics fail startup and
invoke the owner's existing cleanup; the guarded fallback remains responsible
for restoration. The approved provisional decision explicitly uses a 2,300,000-token startup
floor, with 2,350,210 retained as the open full-qualification target. Missing
approval or open gates cannot authorize this exception.

Exa confirmed the [native metrics contract](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/api.md);
pinned `helios/src/server/metrics.rs` defines total pages as the per-rank pool and
total tokens as pages times page size. This capacity is before checkpoint
retention, so admission/pressure tests remain necessary. Local vLLM activation/calibration handling,
exllamav3 state ownership and TensorFold checkpoint arithmetic were reviewed; none justifies assuming a fixed pool across starts. The same
guard runs after boot and watchdog recovery. One focused test rejects a one-page
shortfall, the observed short pool and inconsistent/missing metric evidence.
