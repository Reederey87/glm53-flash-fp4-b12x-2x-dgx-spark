# Post-warmup host ownership diagnostic

Pre-registered terminal diagnostic, not an optimization or serving qualification.
Dependency of TODO3, which remains open. Exa research and the local vLLM,
exllamav3, TensorFold, FlashInfer and Flare source review precede this patch;
see [ownership research](../research/host-ownership.md). Native device-cache
return failed (2MiB only); it is removed from this diagnostic recipe.

One observation: after the original worker warmup frame exits, read pinned host
allocator owned/active counters, CUDA allocated/reserved/free/total, OS memory
fields and up to eight container process RSS/PSS records. No tensor reads,
snapshot history, new synchronization, collection, cache clear or heap trim.
RSS/PSS are overlapping views of unified memory, not additive to CUDA counters.
No process command lines, environment, prompts or model data are read.

Each rank emits one <=4096-byte atomic record and waits at that boundary for
120s, then raises an intentional terminal exception. It never returns into
the later engine allocation known to breach the floor. The supervisor stops
both ranks immediately after both validated records arrive; 120s is a bounded
fallback if records or supervisor disappear. An incomplete/missing record fails
the diagnostic, and all exits retain stop-only recovery. No automatic restart.

Controls: original image3b5da79c, checkpoint76348ddb, TP2, target B12X, Humming
MTP3,4seats,1M context,4096batch,17G FP8 KV/pool2,350,210; native allocator,
common passive trace and postload0.80 bound restored1.0 before capture; unchanged
drivers/kernel, observer/log lifetime. The rejected device-cache clear is absent.

Before deployment require exact source pin/AST-preserving transform, CPU
contracts, lifecycle verification, final independent Astra review and both-node
tiny real pinned-CUDA API probes without loading checkpoint/server.

Require both actual rank/image/profile and installed helper/worker hashes;
complete target/MTP bound and trace receipts; >=4GiB postload minima, >=2GiB
all observed host samples; exactly one ownership record per traced worker PID,
valid counters and bounded process coverage. Existing independent memory guard
remains active. Planned nonzero termination is expected and must be distinguished
from an unexplained crash by diagnostic-captured.txt plus both validated receipts.

Fresh single-use local/ab-host-ownership, unit b12x-recipe-window@host-ownership.
Stop-only cleanup must verify both model containers absent, canonical ledger
restored, proxy/watchdog off. No health/smoke/speed claim. Use the ownership data
to choose the next single treatment; no repeat of a terminal task or floor change.
