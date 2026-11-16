# Approved provisional production and research pause

On2026-11-16 the user paused research, then explicitly selected the current
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
The nine focused production/watchdog tests pass, including rejection of missing
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
