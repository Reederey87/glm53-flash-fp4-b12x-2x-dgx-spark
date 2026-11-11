"""Summarize passive startup logs, including a partial unsafe boot."""
import argparse
import json
from pathlib import Path

MARKER = "B12X_STARTUP_MEMORY "


def summarize(log, require_complete=False):
    records = []
    for line in log.splitlines():
        if MARKER not in line:
            continue
        record = json.loads(line.split(MARKER, 1)[1])
        if record["trace_version"] != 1 or record["integrated"] is not True:
            raise ValueError("unexpected trace version or non-integrated device")
        for key in ("allocated", "reserved", "releasable", "max_allocated", "pid", "utc_ns", "monotonic_ns"):
            if type(record[key]) is not int or record[key] < 0:
                raise ValueError("invalid trace numeric field " + key)
        if record["releasable"] != record["reserved"]-record["allocated"]:
            raise ValueError("inconsistent allocator accounting")
        records.append(record)
    if not records:
        raise ValueError("no startup trace records; instrumentation not proven")
    pids = {r["pid"] for r in records}
    if len(pids) != 1:
        raise ValueError("mixed worker processes in startup trace")
    phases = [r["phase"] for r in records]
    if require_complete and (phases[0] != "postload-enter" or
            phases[-1] != "postload-exit" or
            phases.count("postload-enter") != phases.count("postload-exit")):
        raise ValueError("incomplete post-load trace")
    return {"records": records, "pid": next(iter(pids)), "last_phase": phases[-1],
            "minimum_available": min(r["host"]["MemAvailable"] for r in records),
            "maximum_reserved": max(r["reserved"] for r in records),
            "maximum_allocated": max(r["max_allocated"] for r in records),
            "release_calls": sum(r["phase"] == "release-after" for r in records),
            "released_calls": sum(r["phase"] == "release-after" and r["released"] is True for r in records)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("log", type=Path)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    print(json.dumps(summarize(args.log.read_text(), args.require_complete), indent=2))
