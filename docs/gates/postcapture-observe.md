# Terminal ownership observation after real graph capture

One passive diagnostic relative to retained startup-pinned Humming A: capture
one source/PID-bound all-arena heap, process/PSS, CUDA/pinned and retained-owner
snapshot after the actual V2 capture method's existing GC and workspace lock,
then hold. Controller stops both ranks; second warmup and serving never run.
The decorator is baked as observe_after_capture by install.py --observe.
run.sh requires explicit B12X_POSTCAPTURE_MODE=observe; missing/unknown mode
fails installation before load. Runtime observation cannot call malloc_trim.

Fresh Exa/current local-tree research and matched native experiments rejected
cleanup qualification:512MiB fixtures lost~504MiB RSS, but head available gains
after fixed3s were49.6/87.0MiB, below128MiB. Controls changed-6.8/+23.6MiB.
Worker gains94.9/197.4MiB were inconsistent. PSS confirmed private anonymous
backing; KSM/huge pages/swap were absent. No longer wait/larger fixture/lower
gate is justified. Retain those failures; this is a different diagnostic, not
a cleanup or improvement pass. Gate docs/gates/postcapture-heap.md stays failed.

Independent review caught and fixed needs_capture vs _graphs_captured semantics,
unbounded open_memstream reporting and pointers measured after treatment.
The observer uses the pinned manager's completion flag, fixed128KiB fmemopen
with overflow/error rejection, and a probe with pointers captured before the
boundary. Exact source hashes and real native probes must be reviewed again.

Controls: same image3b5da79c/checkpoint76348ddb, TP2/RoCEnante, targetb12x/B12X,
draftHumming/MTP3/B12X,4seats/1Mcontext/4096batch,17GFP8/block256/pool2,350,210,
default allocator/prefix/chunking/Max reasoning, driver580.173.02/kernel6.17.
Common passive quant trace,0.80 postload cap restored1.0 and measured pre-KV
pinned return retain their existing4GiB/256MiB/128MiB gates. No extra GC/sync,
cache clear, stack change, trim, graph resize or warmup omission in a server.
The server is intentionally never allowed past this terminal boundary.

Before restart: freeze exact bytes, final independent review, CPU/AST/syntax,
isolated lifecycle, pinned frontend equality and both-node/device real capture
probes. Probe uses actual capture/GC/workspace lock and actual manager predicate,
retains prepared B12X and pinned-copy graphs, forbids trim/compiler/loader and
requires3correct replays each plus unchanged pre-boundary pointers. No model.
Usual source/image/env/hash snapshots, freshoutput and>=90GiBfree/>=100GiBavail.

Actual both-node records: exactly one observe phase after graph-finished log,
same worker PID/postload trace, pinned runner/helper/GC/graph/workspace/plan
hashes, original signed capture metric, completed manager/locked workspace,
fraction1.0/nonzero retained owners,17G, valid CUDA/pinned/process/PSS/heap
counts. Require all existing trace/bound/pinned-return proofs before declaring
diagnostic captured. Heap free chunks do not prove resident reclaimability;
PSS/RSS/CUDA counters overlap and must not be summed as node usage.

Continuous2GiB floor unchanged, including snapshot. Any unsafe/invalid/missing
record fails closed. A below-floor raw snapshot may remain forensic evidence,
but is not a valid diagnostic-captured pass. No health/smoke/parity/matrix or
performance/adoption/TODO3 completion claim from this terminal diagnostic.
Missing hook or unexpectedly returned startup must also stop before smoke.

Fresh local/ab-postcapture-observe; unit b12x-recipe-window@postcapture-observe.
All exits stop-only: canonical append-only ledger restored, both model objects
absent, proxy/watchdog off. Never restart this output or unsafe A for metrics.
