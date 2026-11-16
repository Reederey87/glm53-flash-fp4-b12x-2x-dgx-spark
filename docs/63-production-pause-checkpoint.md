# Approved provisional production and research pause

On 2026-11-16 the user paused research, then explicitly selected the current
Flare candidate for production after its seven API checks. This supersedes the
earlier requirement to finish all research gates before adoption. It does not
turn unfinished or failed tests into passes. The release decision is
`recipes/flare-production-decision-20261116.json`; status is
`approved-provisional`, never `qualified`.

## Frozen release

Native manifest127424e9, binaryb2eb310b, core identitydf214696 and primary
SHA2c47847a remain unchanged. NVIDIA checkpoint76348ddb, Flare5a4e867,
FlashInfer4fd836dc, TP2/four slots/MTP3/chunk4096, latency policy, reserve4GiB,
trace off, native dense activations and omitted reasoning=Max. No warmup
experiment, fractional reserve, new kernel or scheduler change is adopted.

The existing runtime launcher41b65a remains in place. Production supervision
is installed separately with exact recipe/core fingerprints and a hashed release
decision. The fully qualified capacity floor remains2,350,210; this explicitly
approved provisional release checks2,300,000 at every startup/recovery, preserving
the current reserve and quantization. Historical starts measured2,331,392–2,343,168.
The ten focused production/watchdog tests pass, including rejection of missing
approval, missing open gates, pin drift and an unauthorized capacity override.

Exa rechecked the official systemd timer contract and NVIDIA capacity metrics;
the prior docs/27 review and local Flare/vLLM/exllamav3/TensorFold lifecycle and
memory contracts remain applicable. No performance improvement is inferred from
functional smoke or this operational release decision.

## Cutover and rollback

Complete the already-triggered B12X restoration and independent smoke first.
Snapshot both ledgers, files and startup ownership. Stage production scripts
atomically and install the head owner/watchdog/proxy units. Arm a disk-persistent
absolute UTC rollback deadline with an OnBoot recheck and pending marker before
disabling B12X startup/watchdog/proxy. Retain both original B12X images and tree.

Append the selected Flare arm, pin both nodes, and start only through
`b12x-flare-production.service`. Verify exact native bytes/argv, both ranks,
capacity, API7/7 and the existing external8000 endpoint. Check watchdog recovery,
then a controlled reboot with new boot IDs and post-boot generation. Preserve
the fallback until these operational checks are complete. No driver/kernel change.
Operational results and receipts are appended below after observation.

## Resume later

Start with this document and `spec/TODO.md`. Do not run an old setup/controller
blindly: many controllers assume B12X is the production owner. Rebase their
preconditions and rollback target onto this Flare production checkpoint first,
using a new window ID and Exa-first review. Existing window directories are
immutable evidence, not resumable jobs.

- Docs/62 closes full MTP replay:5/5 per rank, original bounds, verified B12X recovery.
- Docs/60 completes loss-free native diagnosis, distinguishing cold discovery,
  prefill/refresh decode interference and unresolved visible-only gaps.
- Docs/50 remains failed:10/80 adverse overlapping medians. Keep every result.
- Docs/53 generation was stopped at user request on11:21:29 UTC. Preserve the
  complete baseline and partial candidate; never compare the partial run as a pass.
- Docs/59 and61 warmup-only client/controller are frozen and staged but unrun.
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

Local review: Flare's head dispatch occurs after argument validation; vLLM waits
on explicit worker READY messages; TensorFold distinguishes process exit from
health; exllamav3's TP validation does not supply a systemd readiness contract.
No engine/kernel technique is needed for this orchestration race. Ten focused
production/watchdog tests pass, including delayed dispatch and subsequent failure.
The first memory guard remained running during B12X recovery and stopped at a
B12X startup memory-floor breach; its sample is retained, not counted as a
healthy Flare production observation.

The 11:37 retry started both ranks, reported 2,339,328 cache tokens and passed
API7/7. Its activation controller then exited7 on an immediate external proxy
health connection, before the Type=exec proxy finished binding. Rollback ran
automatically; both native ranks exited cleanly. This is an endpoint readiness
race, not a failed model smoke. The next frozen controller retries connection
refusal with a 60-second retry budget and 5-second per-transfer timeout. Exa
checked [curl's official retry contract](https://everything.curl.dev/usingcurl/downloads/retry.html).
The proxy's asynchronous bind and vLLM/TensorFold startup health loops support
bounded polling. No proxy, model, numerical bound or serving knob is changed.
