# CuTe AOT backing and retained owners

The actual terminal capture observation failed the head's 2 GiB floor before
second warmup. Only about 10 MiB of free glibc chunks remained. Another trim is
not justified. Anonymous RSS is still unattributed; existing 228 counts are
program-key/owner tuples, not distinct engines or duplicate binary copies.

Fresh Exa research precedes any load-path change. NVIDIA's
[AOT guide](https://docs.nvidia.com/cutlass/latest/media/docs/pythonDSL/cute_dsl_general/dsl_ahead_of_time_compilation.html)
supports loading both exported objects and linked shared libraries, subject to
matching runtime ABI/version metadata. It makes no memory-saving promise.
The [dynamic-loading example](https://github.com/NVIDIA/cutlass/blob/dcf215af/examples/python/CuTeDSL/dsl_tutorials/export/run_with_dynamic_loading.cpp)
passes object bytes in one path and an empty object buffer plus a shared-library
path in the other. Both paths retain an execution engine and GPU module owners.
Never unload those owners merely because one graph replay succeeds.

The exact installed compiler stages a private copy of the canonical object,
validates it, then creates ExternalBinaryModule. The returned callable has no
IR module or compiler artifacts. Blindly dropping MLIR or resetting caches is
unsupported by that ownership path. Installed NVIDIA ExternalBinaryModule
always selects JITLink; it documents a duplicate-section crash with MCJIT.
Switching link engines is not an acceptable substitute experiment.

After Exa, the five local trees were checked: vLLM's prepared B12X lifecycle;
FlashInfer compile-plan/scoped retained owners and compiler cache; EXL3's UMA
memory reserves; Flare's preparation host-memory and inventory; TensorFold's
memory-profile/graph lifetime guidance. None establishes a safe method to drop
live native engines. Flare inventories stored fields rather than invoking
properties; that is useful for a future bounded ownership snapshot.

The stopped model's distinct engine identities cannot be reconstructed from
the current receipts. A future in-process snapshot must distinguish scopes,
owner/cache roots, program keys, executable wrappers, engine wrappers and
already-created modules. Use source-allowlisted stored dictionaries, with caps
and explicit incomplete coverage. Generic getattr can load a deferred program,
record ownership or initialize a CUDA library. Do not use it as a heap walker.

First audit canonical artifacts offline, without loading them or using GPUs.
The selected cache root is /home/nvidia/.cache/b12x/compile on each node.
Canonical paths are <key[:2]>/<key>.o plus a version3 manifest. Stream-check
manifest key, object length and SHA256; report section categories separately.
[ELF section semantics](https://man7.org/linux/man-pages/man5/elf.5.html) and
[symbol values](https://refspecs.linux-foundation.org/elf/gabi4+/ch4.symtab.html)
define allocated sections, file-less NOBITS and section-relative relocatable
symbol offsets. Embedded payloads are subsets of section bytes. Missing exact
payload symbols mean unknown coverage. Per-path and unique-content totals are
different; neither represents resident RAM or live engine multiplicity.

Only after a reviewed audit should a model-free loading experiment be selected.
Compare the same canonical object bytes with shared libraries linked from
private copies, keeping symbol prefix, metadata, runtime ABI and GPU bytes.
Measure anonymous/file/total PSS and node headroom independently. A shift from
anonymous to file PSS is not itself physical savings. Preserve strong owners,
forbid fallback compilation during replay, and require native graph correctness
before considering a separately gated checkpoint window. No such window is
cleared by this source audit.

Actual bounded audit:23CPU regression tests passed;1684/1680 unique objects
verify on head/worker,87,217,976/85,465,976 file bytes. Expected export payload
symbol coverage is unknown for every object; no zero-payload inference.
Matched fresh-process32-object host-loading comparison, reviewed at371a3f8,
showed only3,592,192/3,710,976bytes lower incrementalPSS for shared libraries.
AnonymousPSS differences were4,968,448/5,087,232bytes, partly offset by filePSS.
Same inventories, provider/runtime libraries and generated shared hashes;
identical linking before baseline, no GPUs or initialized executors. These
small exploratory effects establish neither physical savings nor native graph
correctness and do not justify a checkpoint retry. Full receipts and limits:
`receipts/cute-artifact-audit/outcome.md`.
