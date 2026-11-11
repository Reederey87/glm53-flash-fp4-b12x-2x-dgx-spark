"""Passive snapshots in an already initialized model worker; no tensor reads."""
import json
import os
import time


def snapshot(phase, device, name="", method="", released=None):
    # Imported only by the patched loader, after its normal torch imports.
    # Never synchronize, clear caches, reset peaks or create a CUDA context.
    import torch
    from vllm.platforms import current_platform

    if device.type != "cuda" or not torch.cuda.is_initialized():
        raise RuntimeError("startup trace requires an initialized CUDA worker")
    mem = {}
    with open("/proc/meminfo") as source:
        for line in source:
            key, value = line.split(":", 1)
            if key in ("MemTotal", "MemAvailable", "MemFree", "Cached", "SReclaimable"):
                mem[key] = int(value.split()[0]) * 1024
    allocated = torch.accelerator.memory_allocated(device)
    reserved = torch.accelerator.memory_reserved(device)
    record = {"trace_version": 1, "phase": phase, "monotonic_ns": time.monotonic_ns(),
              "utc_ns": time.time_ns(), "pid": os.getpid(), "name": name,
              "method": method, "allocated": allocated, "reserved": reserved,
              "releasable": reserved-allocated,
              "max_allocated": torch.accelerator.max_memory_allocated(device),
              "integrated": current_platform.is_integrated_gpu(device.index),
              "host": mem, "released": released}
    # One short write (no logging queue/thread or retained tensor references).
    line = "B12X_STARTUP_MEMORY " + json.dumps(record, separators=(",", ":")) + "\n"
    if len(line.encode()) > 4096:
        raise RuntimeError("startup trace record exceeded atomic-write bound")
    os.write(2, line.encode())
