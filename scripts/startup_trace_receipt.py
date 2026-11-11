"""Summarize passive startup logs, including a partial unsafe boot."""
import argparse
import json
import sys
from pathlib import Path

MARKER = "B12X_STARTUP_MEMORY "


def safety(log):
    """Check completed trace lines while a boot log is still being written."""
    for line in log.splitlines(keepends=True):
        marker = next((m for m in (MARKER, 'B12X_WARMUP_CACHE ', 'B12X_HOST_OWNERSHIP ', 'B12X_HOST_TRIM ', 'B12X_COMPILER_RELEASE ', 'B12X_PINNED_RETURN ') if m in line), None)
        if marker is None or not line.endswith('\n'):
            continue
        record = json.loads(line.split(marker, 1)[1])
        if record['host']['MemAvailable'] < 2 * 1024**3:
            raise ValueError('passive trace crossed 2 GiB host memory floor')


def summarize(log, require_complete=False, expected_loader=None, expected_helper=None):
    if require_complete and (not expected_loader or not expected_helper):
        raise ValueError("complete trace requires both pinned installation hashes")
    records = []
    for line in log.splitlines():
        if MARKER not in line:
            continue
        record = json.loads(line.split(MARKER, 1)[1])
        if record["trace_version"] != 1 or type(record["integrated"]) is not bool:
            raise ValueError("unexpected trace version or invalid integrated flag")
        for key in ("allocated", "reserved", "releasable", "max_allocated", "pid", "utc_ns", "monotonic_ns"):
            if type(record[key]) is not int or record[key] < 0:
                raise ValueError("invalid trace numeric field " + key)
        if record["releasable"] != record["reserved"]-record["allocated"]:
            raise ValueError("inconsistent allocator accounting")
        for field, expected in (("loader_sha256", expected_loader), ("helper_sha256", expected_helper)):
            if expected is not None and record.get(field) != expected:
                raise ValueError("incorrect installed " + field)
        records.append(record)
    if not records:
        raise ValueError("no startup trace records; instrumentation not proven")
    pids = {r["pid"] for r in records}
    if len(pids) != 1:
        raise ValueError("mixed worker processes in startup trace")
    phases = [r["phase"] for r in records]
    state = "postload-enter"
    module_key = None
    for record in records:
        phase = record["phase"]
        if state == "quant-or-attention":
            if phase not in ("quant-before", "attention-enter"):
                raise ValueError("missing quant or attention boundary")
        elif phase != state:
            raise ValueError("missing/reordered startup boundary: expected " + state)
        if phase == "postload-enter": state = "quant-or-attention"
        elif phase == "quant-before":
            module_key = (record["name"], record["method"])
            state = "quant-after"
        elif phase in ("quant-after", "release-after"):
            if (record["name"], record["method"]) != module_key:
                raise ValueError("mismatched quant module boundary")
            if phase == "release-after" and type(record["released"]) is not bool:
                raise ValueError("missing actual release-helper result")
            state = "release-after" if phase == "quant-after" else "quant-or-attention"
        elif phase == "attention-enter": state = "attention-exit"
        elif phase == "attention-exit": state = "postload-exit"
        elif phase == "postload-exit": state = "postload-enter"
    if require_complete and state != "postload-enter":
        raise ValueError("incomplete post-load trace")
    return {"records": records, "pid": next(iter(pids)), "last_phase": phases[-1],
            "integrated_flags": sorted({r["integrated"] for r in records}),
            "minimum_available": min(r["host"]["MemAvailable"] for r in records),
            "maximum_reserved": max(r["reserved"] for r in records),
            "maximum_allocated": max(r["max_allocated"] for r in records),
            "release_calls": sum(r["phase"] == "release-after" for r in records),
            "released_calls": sum(r["phase"] == "release-after" and r["released"] is True for r in records)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("log", type=Path)
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--expected-loader")
    parser.add_argument("--expected-helper")
    parser.add_argument("--safety-only", action="store_true")
    args = parser.parse_args()
    if args.safety_only:
        safety(args.log.read_text())
        sys.exit(0)
    print(json.dumps(summarize(args.log.read_text(), args.require_complete, args.expected_loader, args.expected_helper), indent=2))
