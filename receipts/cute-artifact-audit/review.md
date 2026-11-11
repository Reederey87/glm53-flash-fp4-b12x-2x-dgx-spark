# Independent review scope

Astra reviewed the offline scanner and identified section-overlap accounting,
payload symbol type, manifest shape, nonexistent roots, file-race/bounds and
deduplication gaps. Corrected scanner db5bd18f and focused tests cd601ff1 address
those findings; all23 CPU tests pass. Actual corrected node inventories were
rerun and match the preliminary ordered object keys and digests.

Final review cleared load_feasibility.py371a3f8 only for matched fresh-process
CPU-only loading feasibility: completedv2 inventory, read-only canonical mount,
no exposed GPU devices, runc/capability-drop isolation, matching preparation and
provenance, strong owners and no initialized executors. Native initializers may
execute; compiler version is recorded without a binary hash. These limits are
preserved in outcome.md. No graph or checkpoint deployment was cleared.

Follow-up recommendation: prefer a bounded source-allowlisted live-owner
inventory before KV allocation to an unsupported fork intervention. Historical
post-profile headroom was20.52/21.37GiB, distinct from earlier10GiB postload
minima. Any diagnostic needs fresh admission, model-free collector validation,
frozen bytes, lifecycle checks and final Astra review before deployment.
