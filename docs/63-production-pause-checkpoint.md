# Approved provisional production and research pause

On 2026-11-16 the user paused research, then explicitly selected the current
Flare candidate for production after its seven API checks. This supersedes the
earlier requirement to finish all research gates before adoption. It does not
turn unfinished or failed tests into passes. The release decision is
`recipes/flare-production-decision-20261116.json`; status is
`approved-provisional`, never `qualified`.

## Current operational result — 2026-11-16 UTC

**Flare is serving production on both Sparks.** The user-approved provisional
release is installed, boot enabled and verified. Research remains paused.

| Check | Observed result |
|---|---|
| Final activation | 12:06:58; exact native/core identities, API 7/7, proxy generation |
| Controlled watchdog recovery | 12:09:45; both ranks restarted, API 7/7 and generation; exactly one new persisted attempt |
| Two-node reboot | Both boot IDs changed; owner started automatically and waited for the worker |
| Post-boot verification | 12:14:04; both native identities, API 7/7, generation, capacity and persisted watchdog history |
| Cache pools | Activation 2,331,392; recovery 2,339,328; boot**2,347,264** tokens |
| Memory | 59 final-window and 30 post-boot observations; all original floors passed |
| Remote client | Mac health/generation passed via SSH forwarding to the same proxy, before and after reboot |
| Temporary adoption fallback | Pending marker archived; timer disabled/inactive at 12:15:45 |
| Host versions | Both unchanged: kernel 7.0.0-1025-nvidia, driver 580.178.04 |
| Local validation | 100 tests pass; all adoption helper shell syntax and documentation links checked |

Current owner invocation: `ebbafca3760546538525a65d4403ccfb`. Boot IDs:
head `de8eb78d-969e-4f6f-86f6-b7c71150f7b3` → `db2cd8bf-2592-484e-818b-dd0e7fd47959`;
worker `34470ec3-fd23-40aa-a3e9-7737a3c9afdc` → `cee3a443-e4f0-42c7-b28e-faee0a960a39`.
Two watchdog attempts (one earlier failed, one successful) remain in its six-hour
ledger; no budget was reset. The watchdog and proxy remain enabled/active, while
B12X startup/watchdog/proxy remain disabled. Both original B12X images and its
runtime tree remain available for rollback.

Final monitored minima in GiB: activation/recovery head free 1.732/available 10.798,
worker free 1.947/available 11.839; post-boot head free 1.798/available 10.826,
worker free 1.740/available 11.756. The reboot monitor started at 12:13:08; these
values describe the retained monitoring intervals, not unobserved boot time.

Receipts: `receipts/flare-qualification-20261115/production-summary.json`,
`production-retry-20261116T120500Z-*` and the two remote-client receipts.
Earlier failed attempts and all automatic B12X recovery evidence remain under
separate production prefixes. Direct access from a connected tailnet client is
still unverified; the Mac and worker probes lacked that route.

## Frozen release

Native manifest 127424e9, binary b2eb310b, core identity df214696 and primary
SHA 2c47847a remain unchanged. NVIDIA checkpoint 76348ddb, Flare 5a4e867,
FlashInfer 4fd836dc, TP2/four slots/MTP-3/chunk 4096, latency policy, reserve 4 GiB,
trace off, native dense activations and omitted reasoning=Max. No warmup
experiment, fractional reserve, new kernel or scheduler change is adopted.

The existing runtime launcher 41b65a remains in place, exactly
`scripts/flare_run.py` from kit commit `3b0f6db`. Its companion candidate helper
at that commit hashes `ec57f5a1…`. Do not bulk-sync newer fractional-reserve
wrappers into production. The selected native build is reconstructed from its
manifest and pinned patch, not from an unqualified working-tree default. Production supervision
is installed separately with exact recipe/core fingerprints and a hashed release
decision. The fully qualified capacity floor remains 2,350,210; this explicitly
approved provisional release checks 2,300,000 at every startup/recovery, preserving
the current reserve and quantization. Historical starts measured 2,331,392–2,343,168.
The twelve focused production/watchdog tests pass, including rejection of missing
approval, missing open gates, pin drift and an unauthorized capacity override.

Exa rechecked the official systemd timer contract and NVIDIA capacity metrics;
the prior docs/27 review and local Flare/vLLM/exllamav3/TensorFold lifecycle and
memory contracts remain applicable. No performance improvement is inferred from
functional smoke or this operational release decision.

## Registered cutover and rollback procedure (completed)

Complete the already-triggered B12X restoration and independent smoke first.
Snapshot both ledgers, files and startup ownership. Stage production scripts
atomically and install the head owner/watchdog/proxy units. Arm a disk-persistent
absolute UTC rollback deadline with an OnBoot recheck and pending marker before
disabling B12X startup/watchdog/proxy. Retain both original B12X images and tree.

Append the selected Flare arm, pin both nodes, and start only through
`b12x-flare-production.service`. Verify exact native bytes/argv, both ranks,
capacity, API 7/7 and the existing external8000 endpoint. Check watchdog recovery,
then a controlled reboot with new boot IDs and post-boot generation. Preserve
the fallback until these operational checks are complete. No driver/kernel change.
Observed operational results are summarized above; the historical corrections below remain evidence.

## Resume later

Start with this document and `spec/TODO.md`. Do not run an old setup/controller
blindly: many controllers assume B12X is the production owner. Rebase their
preconditions and rollback target onto this Flare production checkpoint first,
using a new window ID and Exa-first review. Existing window directories are
immutable evidence, not resumable jobs.

- Docs/62 closes full MTP replay: 5/5 per rank, original bounds, verified B12X recovery.
- Docs/60 completes loss-free native diagnosis, distinguishing cold discovery,
  prefill/refresh decode interference and unresolved visible-only gaps.
- Docs/50 remains failed: 10/80 adverse overlapping medians. Keep every result.
- Docs/53 generation was stopped at user request on 11:21:29 UTC. Preserve the
  complete baseline and partial candidate; never compare the partial run as a pass.
- Docs/59 and 61 warmup-only client/controller are frozen and staged but unrun.
  No startup entry point invokes that experiment.
- Docs/54 fractional reserve/capacity window is unrun; its new wrappers are
  not the production runtime launcher. Do not stage them implicitly.
- Decode-aware prefill/refresh limiting and token-publication diagnosis are
  researched options only; no implementation is adopted.

PR #2 carries all integration code and receipts. `spec/` and agent metadata stay
git-ignored; the public resume record is this document. Research stays paused
after operational delivery, documentation and GitHub synchronization.

## Startup readiness correction

The first activation at 11:30 UTC restored B12X automatically after the owner
observed the worker as inactive before the head dispatched it. The native model
was not changed. Exa confirmed that systemd `Type=exec` proves execution, not
application readiness ([official service documentation](https://freedesktop.org/software/systemd/man/latest/systemd.service.html)).
A full `Type=notify` conversion would require changes to the rank supervisor;
the owner already performs bounded application-level readiness. It now allows
only the worker's initial inactive state, within the existing 900-second deadline.
A failed rank, a missing head, or a worker disappearing after startup still fails.
Both active ranks, HTTP health, capacity and all seven API smoke checks remain required.
The later recovery correction below additionally dispatches the worker before
starting the head; initial inactive tolerance alone did not cover retained failure.

Local review: Flare's head dispatch occurs after argument validation; vLLM waits
on explicit worker READY messages; TensorFold distinguishes process exit from
health; exllamav3's TP validation does not supply a systemd readiness contract.
No engine/kernel technique is needed for this orchestration race. Ten focused
production/watchdog tests pass, including delayed dispatch and subsequent failure.
The first memory guard remained running during B12X recovery and stopped at a
B12X startup memory-floor breach; its sample is retained, not counted as a
healthy Flare production observation.

The 11:37 retry started both ranks, reported 2,339,328 cache tokens and passed
API 7/7. Its activation controller then exited7 on an immediate external proxy
health connection, before the Type=exec proxy finished binding. Rollback ran
automatically; both native ranks exited cleanly. This is an endpoint readiness
race, not a failed model smoke. The next frozen controller retries connection
refusal with a 60-second retry budget and 5-second per-transfer timeout. Exa
checked [curl's official retry contract](https://everything.curl.dev/usingcurl/downloads/retry.html).
The proxy's asynchronous bind and vLLM/TensorFold startup health loops support
bounded polling. No proxy, model, numerical bound or serving knob is changed.

## Local delivery validation

All 100 local unit tests pass. The initial sandboxed run could not bind the Unix
notification socket used by one memory-watch test; the same complete suite
passed with socket access. This is separate from hardware qualification.

## Activation observed

The final activation completed at 11:47:00 UTC; its independent identity and
external-generation verification completed at 11:47:22 UTC. Both native ranks
match the approved binary/manifest; the head core SHA matches the accepted core.
The startup reported 9,091 pages ×256 tokens = **2,327,296 tokens**, passing the
explicit provisional floor while remaining below the original target. All seven
checks passed, omitted reasoning still defaults to Max, and a public READY
response passed through the tailnet listener. Owner, watchdog and proxy are
enabled; conflicting B12X units are disabled and both containers are absent.

A direct Mac-to-tailnet health check timed out: this Mac routes 100.125.23.98
through its ordinary 10.0.0.1/en1 gateway, with no Tailscale CLI found in the
standard installation paths. The head's tailnet listener health/generation
checks passed. This is a client reachability limitation; no network configuration
was changed. An actual peer tailnet check and post-reboot checks follow below.

## Recovery ownership correction

The first controlled worker-stop check consumed one persisted watchdog attempt
and dispatched an owner restart. The worker retained its previous failed state
until a new invocation was launched; readiness inspected that old failure before
the head's delayed dispatch, failing at 11:48:38 UTC and restoring B12X. This
failed recovery is retained and must not be counted as a passed watchdog gate.

The production owner now dispatches the worker's Type=exec unit synchronously
before the head, after both-node cleanup and memory gates. Neither command waits
for native rendezvous, avoiding a launch deadlock. The head supervisor's existing
start of an already-running worker is idempotent. No reset-failed or watchdog
budget clearing is added. Actual failed startup still fails readiness. Exa
reviewed the [systemctl contract](https://www.freedesktop.org/software/systemd/man/latest/systemctl.html);
local Flare rendezvous, vLLM's create-all-workers-before-readiness, exllamav3
collective initialization and TensorFold launch ownership support this ordering.
Two focused tests prove worker-before-head dispatch and that a worker dispatch
failure prevents head launch. All 100 local tests pass.

## Client-network probe retained separately

The ordered-start owner passed API 7/7 at 11:57:04 UTC. Its subsequent exact
identity and tailnet-listener generation verification passed. An added peer
tailnet probe timed out and the operational controller automatically restored
B12X before the planned watchdog injection. This was an invalid client-network
precondition for that controller, not an observed model or owner failure.
The head Tailscale backend reports Running/Online with no health warnings.
The worker has no tailscale command on PATH; its route to the head's100.x address
uses its ordinary LAN gateway. The Mac likewise lacks a tailnet route.

Exa's [Tailscale connection prerequisites](https://tailscale.com/docs/how-to/connect-to-devices)
require a connected client and policy permitting that route. No client install,
ACL or network change is included in this release. Keep the failed probe receipt
and verify a real remote client through an SSH tunnel to the same head listener.
External tailnet-client validation remains a documented follow-up for a connected
client; it is not silently reported as passed.

## Open work when research resumes

- Rebase old controllers onto the Flare production owner and rollback checkpoint
  before a new window. Preserve existing evidence and preregister new gates.
- Resolve the ten adverse ABBA median points and run the full matched B12X
  matrix. The staged 14-request warmup is only a mechanism proposal; ordinary
  and refresh prefill interference plus visible-only gaps still need evidence.
- Recover and qualify the original 2,350,210-token usable cache target. The
  reserve 3.875 experiment and fractional wrappers are unadopted.
- Complete a new paired generation comparison without changing its assertions,
  plus independent full-model/exported-core correctness.
- Qualify cold concurrent retrieval, million-token admission, hybrid state reuse,
  prefix forks, page boundaries, speculative rejection and memory pressure.
- Optional later work: context parallelism, adaptive/larger MTP, more slots,
  alternative prefill sizes and two-rank disk-prefix retention.
- Separately verify direct tailnet access from a connected client; neither this
  Mac nor the worker currently has that route. No network policy was changed.

The canonical ignored `spec/TODO.md` contains the fuller open-only checklist.
Completed deployment tasks are removed there once their receipts are retained.

## Watchdog recovery observed

The corrected owner completed controlled recovery at 12:09:45 UTC. Two failed
health observations consumed exactly one new persistent attempt, changing the
owner invocation to `b21adcbf22214878afc34442844d7812`. Both native identities,
core hash, capacity, API 7/7 and proxy generation passed. The earlier failed
attempt remains in the ledger; no restart budget was cleared.

A real Mac client then passed health and READY generation through an SSH tunnel
to the head's existing tailnet listener8000, which forwards to native8001.
This verifies the network client/API/proxy path over SSH, not a direct tailnet
route from the Mac. The temporary tunnel was closed after the check.

Both ranks were cleanly stopped at 12:10:23 UTC, with Flare owner/watchdog/proxy
still enabled and the calendar rollback armed. Worker and head accepted the
authorized `shutdown -r now` commands. Post-boot verification is recorded below.
