# Bounded scheduler native diagnosis

The docs/33 diagnostic completed both arms on unchanged artifact127424e9,
wrapper41b65a5a and coredf214696. Each has25 matching cold request bodies,
26 complete prompt histories and360658 prompt tokens. Balanced414 and bounded405
native completions have consecutive fences, zero dropped updates and no
truncation. Both actual native exits were0 with no forced kill after each arm.
All37/36 memory samples passed; minimum free memory was1.828/2.066GiB balanced
and2.036/1.806GiB bounded on head/worker. B12X restoration then started.

## What the capture establishes

The earlier decoder0 p95 jump did not recur: HTTP p95 was0.09946s balanced
versus0.10010s bounded. Gaps over0.2s numbered25 versus22 out of511; the
three-repetition untraced result remains unresolved. One diagnostic repetition
cannot overturn it or qualify performance.

The longest native decode-completion gap was1.309880s balanced: ordinary
prefill1536 GPU0.862s, refresh prefill256 GPU0.349s, then speculative2x4
GPU0.094s. Bounded's1.407650s gap contained ordinary prefill1536 GPU0.859s,
refresh prefill512 GPU0.450s, then the same speculative shape GPU0.094s.
HTTP maxima closely matched these gaps. Unlike the rejected age policy, neither
current arm selected prefill3072 in the measured decode-overlap interval.
Current ordinary prefill choices were1024/1536/2048; refresh and endpoint
shapes also differed. A native generation is not asserted to be an HTTP ID,
and maximum per-rank GPU durations are not absolute device timelines.

Short-arrival phase differences are visible natively. At the second131072-token
prompt, balanced starts with two3072-token ordinary graphs taking1.371/1.419s;
bounded starts with two4096-token graphs taking1.726/1.765s. The first1024-token
prompt is selected2.796s versus3.494s after that long prompt's first selection.
Both short graphs take about0.633s. First HTTP short TTFT is1.494s versus2.202s;
later periodic arrivals alternate their relative advantage as they meet different
in-flight chunks. The native trace has no exact HTTP-admission timestamp, so
this supports a chunk/arrival-phase explanation without proving every queueing
component. No36-second short stall occurred; bounded maximum short TTFT3.029s.

## Implication

The active-decoder cohort correction does not remove ordinary/refresh chunk
interference or history-dependent graph costs. A larger number of repetitions
alone is not a causal fix. Before a new scheduler change, use Exa and pinned
source to evaluate refresh deferral while output is overdue, duration-aware
chunk limits and their prefill-throughput tradeoffs. Counterbalanced fresh-start
comparisons can separate order/history effects; they must retain matched bodies,
all earlier results and the registered2% rule. Do not promote this one trace to
a speed verdict or replace the unresolved p95 criterion with another metric.

Research basis remains docs/32–33: official native completion/cost contracts,
vLLM delivery accounting, NIST blocking guidance and SLO-aware chunk selection.
Exact raw traces, client timings, native identities/exits, memory observations
and reproduced analysis are `bounded-native-*` receipts. Analyzer:
`qualification/analyze_mixed_trace.py`. No native engine change followed this
capture. Component MLA qualification and measured capacity work are independent
remaining gates; production ownership and main merge remain pending.
