# Source-bound selected native-owner inventory

Fresh Exa lookup before critical changes covered NVIDIA's
[JIT ownership/caching](https://docs.nvidia.com/cutlass/latest/media/docs/pythonDSL/cute_dsl_general/dsl_jit_caching.html)
and [Python passive inspection](https://docs.python.org/3.12/library/inspect.html#fetching-attributes-statically).
The [CPython static-inspection cache issue](https://github.com/python/cpython/issues/118013)
also cautions against treating introspection as lifetime-neutral across versions.
This collector avoids generic getattr/hasattr/getattr_static and reads only
stored dictionaries on exact classes resolved from already-loaded pinned modules.

After Exa, the local vLLM preparation lifecycle, FlashInfer retained-program
scope/cache/carrier paths, EXL3 UMA/GC lifetime, TensorFold profiling guidance and
Flare stored-field inventory were checked. Flare's distinction between stored
fields and properties is adopted into this bounded diagnostic. Neither its
engine nor its generic closure/tensor traversal is ported into this launcher.

The exact installed worker releases preparation/profile state before returning
from explicit profiling; common pinned return then validates its actual cache
release. The new decorator sits outside that existing pinned-return decorator,
inside torch.inference_mode, and never returns to KV allocation. Its installer
requires inputea6dc50f, not original668921c6. Removing only the new import and
decorator preserves the input AST. Successful normal return is essential:
inactive fields or the early-set pinned flag alone do not prove completion.

Resolved scopes retain owners AND scoped-cache entries. Both are strong roots;
the weak resident registry is not a complete inventory or an ownership root.
Selected carriers expose explicit dependencies and immutable program keys.
Deferred forwarding may load code; compiled forwarding may record ownership;
native library properties can initialize CUDA. None is invoked by the collector.
Engines are opaque identity nodes. IR/artifact presence and bounded unique
payload lengths are recorded without text, export, inspection of native memory,
or treating Python wrapper identities as measured backing allocations.

The candidate gate is `docs/gates/native-ownership.md`. Existing 17G quant/KV
controls and common trace/bound/pinned gates remain. This is terminal evidence
collection, not a memory cleanup, performance optimization or TODO3 verdict.
Unknown carriers, structural changes, limits and missing providers invalidate
coverage; the supervisor still stops both ranks. Exact source hashes reside in
the collector's PROVIDERS table; extracted vendor bytes remain local.
