# Cleanup not qualified; no checkpoint deployment

Initial4e56fc5 native probes lost~504MiB anonymous RSS but failed the unchanged
128MiB immediate node-gain gate on both nodes. The raw logs are retained.
Matched512MiB CPU fixtures, fixed1.25s resident baselines and3s/50ms observation:
head trim49.6/87.0MiB vscontrols-6.8/+23.6; worker94.9/197.4 vs-.2/+39.4.
This does not establish robust128MiB head gain. Head PSS follow-up confirms
private anonymous backing disappearing, with no KSM/THP/swap in that CPU case;
its node gain was only53MiB. No longer runtime wait, larger fixture or lower
gate was adopted. Physical attribution remains unresolved.

Review caught capture-state, report-buffer and pointer-test defects before any
checkpoint load. Fixes are evaluated as a separately gated terminal observer,
not retroactive cleanup qualification. No model restart or serving measurement
was performed for the failed cleanup candidate.
