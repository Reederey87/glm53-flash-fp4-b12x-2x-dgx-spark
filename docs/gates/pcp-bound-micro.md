# Preregistered PCP policy micro A/B

Status: NOT RUN. Final review and staged-source/control preflights required.

Independent variable: vm.percpu_pagelist_high_fraction0 ->512 on BOTH nodes.
Frozen: exact existing image/kernel/driver, default CUDA host allocator, original
83f453 parent/8e4e sampler/1761 helper,512MiB fixture,3B12X+3host-copy graphs,
active owners/pointers/device counters, min_free1048576/stat_interval1. No model
or API. All model/proxy/watchdog units remain stopped.17G admission stub is not
model-profile evidence. No persistent sysctl config or production adoption.

Exactly one fresh A then one fresh B process/node, same counter/timing wrapper.
Require100GiB available throughout this model-free study, independently of the
unchanged2GiB full-model floor. This is a micro-probe entry/observation control.
No adaptive cap search/retry/wait. Read bounded stock before any treatment,
before fixture, resident, cached, after helper and after rollback. Both-node
topology0-19 and actual present/managed/14orders/4KiB must match. Verify B
high_min=high_max=max(managed//512//20,4*batch); base batches unchanged. Current
high/count may lag these bounds. Distinguish pre-existing stock drain from the
fixture interval. Parent's original immediate interval remains untouched.

Gate: original physical helper128MiB available gain, >=256MiB idle bytes
returned and its unchanged live-state/source/PID gates, on both B nodes; all
graph/pointer/config replays pass; one final marker+clean exit. Separately
report fixed512MiB allocation latency and all stock deltas A/B. One repetition
cannot qualify throughput or a model; a pass only permits design of the next
compound diagnostic, still subject to review. A fail is preserved and stops.

Choose512 before measurement: nominal combined251.719MiB vs default~1GiB stock,
aiming for >=0.5GiB reduction while retaining a nonzero cache.256 nominal494MiB
is less aggressive but leaves less margin against last head1.840GiB. No hard
instantaneous occupancy guarantee or inference-speed claim for either.

Snapshot .env and source hashes both nodes; append only experiment comments
and outcomes. Arm independent user-systemd rollback timers BEFORE the first
write,300s maximum, on both nodes. Controller finally cleanup restores both nodes on
partial application, probe failure or interrupt; timers survive disconnect.
Verify policy0 and original minfree/statinterval after exit, then cancel timers.
Rollback restores policy, not historical page stocks or dynamic high values.
If either restore fails, keep timers armed and do not start any model.
Keep timers armed on any trial error. Require>=240s remaining before either
apply,>=180s before each B probe (60s bound/probe). Rollback closes a per-trial
lease under the same lock as the setter; delayed setters then refuse to apply.
Rollback bypasses unrelated minfree/statinterval drift and reports it afterward.
Timer restore retries on failure; unexpected PCP values are never overwritten.

Writes use the existing root Docker daemon with one explicit sysctl file bind
plus private trial lease/lock files;
no privileged mode or extra capabilities. Failure to mount/write/readback is a
failed trial, never permission escalation to a broader container. Driver580 and
kernel6.17 stay unchanged. No stat_refresh, forced drain, flush or lower gate.
