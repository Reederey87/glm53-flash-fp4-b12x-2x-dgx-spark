# Native scheduler A/B window — registered 2026-11-16 UTC

Do not start until the full CPU scale audit is terminal, its receipts are
validated and B12X restoration is verified. Production adoption is authorized
after qualification; this window does not waive outstanding numerical, capacity,
long-context or lifecycle requirements.

## Frozen artifacts and treatment

Use the same immutable release binary in both native arms:
manifest6626c7854c256178335e664816e8a88e976c921c3e702241eed320ea76e3f397,
binary1fa254f58542219992b6f24c02610d07122fda34431bb943d94366b5053c8b9e,
patch338bbeb0722c80ce86e6fdb1928f09b369fe389c723d6dfde3627ce0201dd5cb.
The sole experimental variable is `FLARE_SCHEDULER_POLICY=balanced` versus
`latency`. Freeze source pins, native-activation coredf214696, checkpoint76348ddb,
TP2, four slots, fixedMTP3, chunk4096, CP-off, reserve4 and T1/top-p.95.
This is a native host-policy build, with no CUDA or exported-weight change.

Freeze the kit/client commit and stage scripts atomically into the runtime tree.
Verify the patch, manifest, executable and dependency hashes on both hosts.
Keep the original CLI and B12X image intact. Snapshot `.env`/file hashes and
enabled-unit states before touching production. Pre-arm automatic B12X restoration
at180minutes; its command must first stop the exact measurement-client units.
The helper does not discover arbitrary clients. Disable the incumbent watchdog,
stop B12X through its unit and require both original idle-memory gates.

Append both `FLARE_NATIVE_ARM=<full manifest hash>` and the policy to each node's
ledger. Start the head native unit, which starts rank1. Before measuring, verify
both native executable hashes, actual argv/policy, native core identity and health.
Start the existing memory observer enforcing MemFree>=1.5GiB and
MemAvailable>=8GiB on both nodes. An observer error, memory violation, allocation
stall, rank failure or corrupt/nonfinite result aborts and restores B12X.

## Balanced control and mixed-workload observations

Run the7-check native API smoke, then `flare_mixed_bench.py --policy balanced`
with run-id `scheduler-latency-20261116`, the pinned tokenizer and a fresh receipt.
The policy label is not activation proof; argv verification above is mandatory.
The client warms once, uses three repetitions and emits75 request observations:

1. Unequal burst:131072/32768/8192/4096 exact prompt tokens, simultaneous arrivals,
   one output token each, four slots.
2. Short arrivals: one131072-token prompt at0seconds, then sixteen1024-token
   prompts at2,4,...32seconds, one output token each. Record the long request's
   progress through final response and every short request's latency. This finite
   workload supplements the sustained-arrival CPU test; it is not an arbitrary
   overload guarantee.
3. Decode overlap: start prose/code chat requests with512 output tokens each.
   After both emit first output, submit32768/4096-token prompts with one output
   token each. Require both decoders still live at prompt arrival and at least
   five later visible deliveries per decoder during the prompt lifetime.

Every prompt must report zero cached tokens. Raw-token lengths must match exactly;
actual completion counts must reach the registered budgets. Timed arrivals must
start within250ms of their scheduled offset, with actual times retained. Match
request hashes, counts and sampling between arms. Missing overlap, early EOS,
incomplete streams or missing usage make a case unqualified. Never silently drop
failed requests or invent per-token times for speculative bursts.

The [official vLLM measurement definitions](https://docs.vllm.ai/en/latest/benchmarking/cli/)
distinguish client TTFT, streaming gaps and amortized TPOT. Exa and pinned local
benchmark/source review support recording the actual delivery times. Here gaps
are explicitly visible-output delivery gaps; no zero-time token samples are
inserted.49 local tests pass, including burst semantics, cold/usage validation,
incomplete streams and insufficient overlap rejection.

## Latency treatment and acceptance

Stop the memory observer and all clients, then both native ranks. Capture clean
terminal state, wait for the original two-node idle-memory gate, and append the
latency policy without changing the binary/core or other settings. Start through
the same native unit, verify both argv/hashes/health, and restart memory monitoring.
This restart gives the arm fresh request/prefix state. Run7-check API smoke,
the same mixed client/run-id and the complete existing `flare_bench.py` matrix:
three reps,8k/16k/32k/64k/128k, c1/2/4/8,200-token prose/code decodes.

Compare all84 rows and315 request hashes to the retained complete B12X reference
using `flare_compare.py`. Keep the existing >2% robust-regression gate for
per-request prefill, decode throughput and acceptance. Compare individual response
times and batch completion as well; improved aggregate prefill cannot mask TTFT.

For the matched mixed observations, retain every repetition and per-request
timing. Reject a separated >2% increase in TTFT, end-to-end latency or decode
delivery-gap p95/max (best candidate worse than1.02 times worst control), or a
separated >2% decrease in decoder throughput. A median regression with overlapping
ranges requires investigation/repetition, not adoption. Require completion of
the long request and all short arrivals; cancellation/retirement remains covered
by smoke and native tests. These are descriptive gates, not confidence intervals.

After performance clients and memory enforcement stop, run the corrected loaded
graceful-shutdown client with the exact active restoration timer. Preserve actual
both-rank exit evidence. Peer-loss, full retrieval, native numerical/state and
capacity gates still require their own evidence; do not declare production ready
from this window alone. Restore B12X on failure or at the deadline. Verify original
images, health, fresh5-check smoke, watchdog/tailnet before disarming fallback.
Revert native selection by appending upstream/balanced on both nodes as needed.
