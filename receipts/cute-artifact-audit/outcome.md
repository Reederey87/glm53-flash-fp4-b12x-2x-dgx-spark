# Offline cache audit and host-only loading comparison

No model deployment, GPU access or kernel invocation. The existing serving
failure remains unresolved; TODO #3 is open. Both models remained absent,
image unchanged, model MainPID0, proxy/watchdog inactive at06:45:25Z.

The corrected scanner passed23 focused CPU tests, including malformed headers,
section overlap, manifest shape/integrity, unknown GPU symbols, deduplication,
file races, symlinks/FIFOs, nonexistent roots and aggregate limits. Both actual
audits completed without errors, with exact v3 manifests and streamed digests:

| Canonical disk artifacts | Head | Worker |
|---|---:|---:|
| Objects / distinct object digests | 1,684 | 1,680 |
| File bytes | 87,217,976 | 85,465,976 |
| Allocated executable section bytes | 4,275,860 | 4,229,024 |
| Allocated read-only section bytes | 73,175,944 | 71,494,616 |
| Allocated writable section bytes | 1,957,784 | 1,945,256 |
| Declared NOBITS bytes | 13,472 | 13,440 |

These are disk/declared section totals, **not RAM**. Payload-symbol coverage is
UNKNOWN for every object: the expected export symbol is absent. One inspected
object instead has a local kernels_binary symbol; its meaning was not assumed.
No zero-GPU-payload conclusion follows. Per-path and unique-content totals
happen to match because every object digest differs. None counts live owners.

The initial scanner reports are retained as preliminary. Corrected inventories
have exactly the same ordered object keys/digests. Full inventories are gzip
compressed with original JSON bytes preserved; summaries omit only artifact rows.

After independent review of probe371a3f8, each arm ran in a fresh CPU-only
container with runc, no GPU device nodes, empty CUDA visibility, dropped
capabilities, no network and read-only canonical cache. Both modes linked the
same32 largest objects from private copies before baseline. Metadata loading
can execute native initializers; no kernel callable was invoked. All32 strong
module/function/engine wrappers remained alive, with no initialized executor.
Within each node, ordered keys, inventory/provider/library provenance and every
generated shared-library digest match across arms. Compiler version text is
recorded; compiler binary hash is not.

| Incremental PSS, bytes | Head | Worker |
|---|---:|---:|
| Object loading | 23,183,360 | 23,085,056 |
| Shared-library loading | 19,591,168 | 19,374,080 |
| Difference | 3,592,192 | 3,710,976 |
| Anonymous PSS difference | 4,968,448 | 5,087,232 |

This is a small exploratory loader effect, not physical-headroom qualification.
Earlier unequal-preparation probes remain labelled exploratory. Neither series
establishes graph correctness, serving speed or checkpoint deployment clearance.
Do not extrapolate32 metadata-only engines to the model's228 program/owner
tuples. No further checkpoint retry is justified by this result alone.

Reproduce: decompress node inventory to a temporary JSON file; mount it and
load_feasibility.py read-only alongside /home/nvidia/.cache/b12x/compile:/cache:ro.
Use the exact image in terminal-state.txt and the isolation flags above. Invoke:

```sh
uv run --offline --no-project --python /usr/bin/python3 /probe.py /inventory.json /cache --mode object --count 32
```

Repeat with `--mode shared` in a separate container. The canonical objects are
never presented writable to the loader or linker. tools.sha256 pins the tools.

Next source-guided evidence is a bounded inventory of distinct live native
owners at an earlier safe boundary. A multiprocessing import-sharing hypothesis
also requires exact CUDA/thread lifecycle checks; it is not cleared for use.
No cache, IR, graph or engine owner has been evicted by this audit.
