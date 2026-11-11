# Preregistered fixture-only matched observation

The first de7fe05 compound probes FAILED on both nodes before the collector.
Both returned512MiB idle allocator bytes, with only-0.219/0MiB immediate
MemAvailable delta. Existing128MiB physical gate is unchanged. They remain
failed; neither source-fixed collector code nor a later study makes them pass.

Run exactly one old/current fixture pair per node, each in a fresh process.
All setup in check_pinned_residency_cuda.py is identical across arms: same image,
prepared B12X/host-copy graphs, current inference/preparation/workspace imports,
unindexedCUDA, helper1761e9ae,512MiB pin fixture and immediate original gates.
Independent variable is the fixture recipe: empty+fill37+delete before stub
versus ones1+list retention+clear inside stub. This compares the old/new fixture
recipes under current common setup, not the complete historical programs.

Sample bounded counters before allocation, while resident, after Python owner
release before helper baseline, and immediately after return OR exception.
Include allocator owned/active/free counts, selfRSS/anonymousPSS and host free,
available, anonymous, unevictable, file cache and slab counters. No observations
inside the helper's original before/after gate interval. No waits, stat_refresh,
extra collection/cache/trim, larger fixture, lower threshold or retry to success.

This is measurement only. Emit failed helper outcomes explicitly; an exit0
means observations collected, not reclamation or compound qualification.
No model/health/smoke/speed or checkpoint-deployment clearance. Preserve the
earlier compound failures and every study result. Final source review precedes
the pair. If attribution remains ambiguous, retain uncertainty rather than
infer physical release from allocator counters or synthesize success flags.
