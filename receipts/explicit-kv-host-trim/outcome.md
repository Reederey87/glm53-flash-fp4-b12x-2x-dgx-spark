# Rejected: insufficient actual host-heap return

The exact reviewed treatment ran once per rank after explicit profiling and
before KV allocation. Head returned1,552,384bytes (1.4805MiB), worker794,624bytes
(0.7578MiB), versus the pre-registered1GiB/rank gate. malloc_trim returned1,
but that boolean was insufficient. Both hooks raised before allocating KV;
the controller eagerly rejected the head proof and stopped the window.

Terminal2026-11-11T03:31:39Z, primary1/recovery0. Verified both model objects
absent, canonical ledger restored, proxy/watchdog inactive. No memory-floor
breach, health, smoke, speed or adoption. TODO3 stays open. Preserve this task.

Actual workerfb8c95d6/helper849183c5 hashes, same traced PIDs366/307, unchanged
CUDA allocated90,342,259,200/reserved90,861,207,552bytes, pinned owned/active
687,867,449/150,996,524bytes, fraction1.0 and original admission17GiB proven.
Host availability before/after stayed21.468/22.195GB; trims took1.182/0.640ms.
Both target/MTP postload cap scopes passed, restored1.0,1817 trace records/rank;
minimum10.134GiB head/11.239GiB worker. The1GiB gate was not relaxed.

Both real compatibility probes had passed the same gate (1.179/1.230GiB) with
live CPU guards/pinned/graph pointers and outputs preserved; that synthetic
fixture did not predict real-model reclamation.43CPU/40Linux lifecycle,
exact source/AST, frontend identity and final review preceded deployment.

Conclusion: an earlier glibc trim does not recover the multi-GiB worker footprint
on this actual path. Anonymous RSS is not proof of unused glibc pages. Next
inspect retained AOT/compiler/preparation objects and their ownership before
any cleanup patch. Flare's release of serialized compiler state is a source
lead, not evidence that vLLM has the same lifetime defect. Preserve live kernel,
tensor and graph owners; do not compensate by shrinking17G or lowering floors.
