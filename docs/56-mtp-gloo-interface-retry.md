# Bind the MTP qualification control group to the fabric

The first docs/52 window failed before numerical replay. Gloo attempted a peer
connection at127.0.0.1 and reported connection refused. Both hostnames resolve
to127.0.0.1; the QSFP interface `enp1s0f1np1` instead holds192.168.177.10/.11.
The fixture supplied the routable rendezvous address but omitted the explicit
Gloo interface selection used by the successful complete-layer fixtures.
Preserve the failed log/XML and wrapper exits; this is not a numerical result.

Exa reviewed the official [PyTorch interface-selection contract](https://docs.pytorch.org/docs/2.15/distributed.html#choosing-the-network-interface-to-use)
and [maintainer explanation of rendezvous versus peer sockets](https://discuss.pytorch.org/t/connect-127-0-1-1-a-port-connection-refused/100802).
The rendezvous address does not bind every Gloo peer socket. Explicit interface
selection is preferable to changing host resolution, opening unrelated firewall
ports or increasing timeouts. Pinned Flare `host_ranks._use_interface` already
maps the selected local IPv4 address to its interface and setsGLOO_SOCKET_IFNAME.

After lookup, checked that helper and the successful layer fixture, vLLM's
Gloo process-group construction, exllamav3's separate CPU/GPU collective owners
and TensorFold's explicit rank/partition handling. The correction reuses Flare's
existing route-selection helper before checkpoint loading. No native collective,
model math, checkpoint, graph geometry, replay assertion or bound changes. The
entire numerical body after device validation is byte-identical to the frozen
first attempt. Do not change either host's network configuration.

## Frozen retry

First run a bounded CPU-only two-host preflight using the same rendezvous and
helper: verify local fabric addresses/interface, sum rank values to3, exchange
the exact rank/address pairs and complete a barrier. No CUDA operation is used.
Retain both actual exit0 results; a failed preflight blocks the GPU retry.

`mtp-replay-bound-window-20261117T030000Z` requires independent original-window
B12X recovery/fresh5/5 and fallback disarm, plus the passing docs/51 feedback gate.
Repeat all five original cases per rank in fresh processes with the same strict
stage/state assertions and same-selection reference. Retain new source hashes,
interface property, per-case XML, native observations and actual wrapper exits.
Keep the original memory floors/idle gates,70-minute controller,65-minute rank
limits,80-minute notifying memory guard and90-minute independent fallback.
Restore B12X and independently verify original images, API/watchdog/tailnet,
absent test/native processes and fresh5/5 before closing this retry.

The new binding is locally syntax checked; GPU retry and CPU network preflight
are not yet executed. The later trace and capacity controllers depend on this
retry's recovery; capacity also requires its successful MTP gate and the still
unmet ABBA performance gate. No production adoption follows a transport fix.

CPU preflight passed both ranks with the exact fabric addresses, all-reduce3,
matching peer exchange and actual exit0. An initial worker SSH wrapper failed
before fixture execution because its relative interpreter path was resolved in
the wrong directory; the corrected absolute-path invocation joined the waiting
head and both completed. No numerical or network setting changed for that fix.

Initial-window recovery/fresh5/5 closed09:56:31 UTC, restore8f9660b2e70a4ec49766d506c532408a,
smoke32b2f8699b1c47a696c266194addc379, both actual exit0/PID0. Fallback disarmed.
The frozen retry started09:56 UTC, controller479e48c55c2d4e7a89d623908467c490,
after source-manifest verification on both nodes. Numerical result pending.

The corrected binding succeeds. Both first cases then fail in legacy FX
compilation at raw Triton residual RMSNorm (77.23/77.03s), before numerical
replay. Docs/57 records the production-capture correction and separate retry.
