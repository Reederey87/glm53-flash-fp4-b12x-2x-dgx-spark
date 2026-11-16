# Peer drain correction — registered loaded lifecycle gate

> Historical architecture or qualification record. Current production, unresolved gates and the research pause: [docs/63](63-production-pause-checkpoint.md). Old window controllers must be adapted before reuse.

## Retained failure and source evidence

Window041500Z completed all75 balanced mixed requests/9 cases with7 API checks.
The strict transition gate then failed: head native exit0 at04:33:50 UTC,
worker native exit-15 at04:33:51 after a requested local shutdown. Neither was
force-killed. The bounded latency arm and full performance matrix did not run.
This is a lifecycle failure, not a performance verdict. Raw balanced receipts
and actual invocation-bound exits are retained under `bounded-*`.

Exa found NVIDIA's [multi-host shutdown contract](https://github.com/NVIDIA/flare-local-inference/blob/main/docs/multi-host.md):
rank zero drains first; peers receive30 seconds after its exit before remaining
peers are stopped. Reconciled with pinned5a4e8679 source:
`flare-cli/src/launch.rs::Peers::finish` and Orbit controller PEER_GRACE/stop_group
implement this bound. `main.rs::serve_peer` releases record service, transport
and model resources after coordinated drain; it does not install the head's
SIGTERM handler. Our wrapper's immediate worker stop can interrupt that cleanup.

Also re-read vLLM's liveness/finally shutdown, exllamav3's explicit resource
cleanup and TensorFold's scheduler-owned stop. A stronger alternative is native
Orbit ownership, but that changes launch/auth/placement and requires a separate
deployment. Changing KillMode alone would not solve this wrapper's explicit
worker SIGTERM. Adopt upstream ordering within the existing supervisor instead.

## Independent change and bounds

Only `scripts/flare_run.py` changes at runtime. After a requested serving stop
and actual head native exit0, poll the worker unit for up to30 seconds, allowing
natural coordinated exit. Then issue idempotent stop for cleanup. Failed heads
and preparation retain immediate peer cleanup. SSH polling is bounded by the
remaining grace; stop dispatch/wait is bounded65s, within the existing180s unit
stop budget alongside the60s native child timeout and interrupted peer probe.

Do not convert signal exits to success or weaken the graceful checker. Actual
native exit and forced-kill records remain authoritative. Local tests cover
natural peer exit before stop, the30s limit, immediate cleanup on failed heads,
and unchanged native-failure propagation.

## Hardware gate before retrying scheduler performance

Window `peer-drain-window-20261116T044500Z`, with60-minute pre-armed restoration.
First close the prior window with original B12X image identities, API health,
fresh5/5 smoke and watchdog/tailnet, then disarm its fallback. Freeze the wrapper
commit; snapshot both original wrapper files/hashes and ledgers; stage atomically.

Frozen controls: artifact127424e9, binaryb2eb310b, coredf214696,
checkpoint76348ddb, **balanced** policy, tracingoff, TP2,4slots,MTP3,chunk4096,
CP-off,reserve4,T1/.95. No native rebuild or production boot adoption.

1. Disarm B12X healer, stop its unit, verify both containers gone and pass the
   original90GiB free/100GiB available gate. Start native through the head unit;
   verify actual binary/argv/core on both ranks and7 API smoke checks.
2. Run `flare_lifecycle.py --action graceful` after observing at least32 generated
   tokens with an active request. Require both ranks terminal within180s, actual
   native exits0/no forced kill, stream termination, and both operation locks free.
   Retain the peer-drain event and exact invocations.
3. After the unchanged memory gate, start the same frozen arm again. Inject
   worker SIGKILL during observed active decode. Require head failure rather
   than masked success, both ranks terminal within180s, HTTP stream termination
   and released operation locks. Retain actual head exit/forced-kill evidence;
   the killed worker cannot write a final native record by design.
4. Restore B12X through its original unit, verify both images, health, fresh5/5
   smoke and watchdog/tailnet, append rollback selection, then disarm fallback.

Use memory enforcement while serving; stop the separate monitor immediately
before each destructive lifecycle probe to avoid a competing restorer. The
independent deadline remains armed throughout. A failed probe queues restoration
and halts the sequence. Before any further GPU start enforce both memory bounds.
If the correction fails, preserve and restore the prior wrapper bytes atomically
only after both native ranks stop; do not claim the old wrapper is qualified.

Only after this gate passes, repeat a fresh matched balanced/bounded75-request
comparison with the corrected wrapper fixed in both arms, then the conditional
full84-row matrix. Do not reuse pre-fix balanced numbers as the sole new control.
