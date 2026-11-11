"""Require actual one-shot heap reclamation and unchanged CUDA/pinned state."""
import argparse
import json
from pathlib import Path

MARKER = 'B12X_HOST_TRIM '


def validate(log, worker, helper, pid, minimum=1024**3):
    rows = [json.loads(line.split(MARKER, 1)[1]) for line in log.splitlines() if MARKER in line]
    if len(rows) != 2 or [r['phase'] for r in rows] != ['before', 'after']:
        raise ValueError('need one complete explicit-profile host trim')
    before, after = rows
    for row in rows:
        if row['version'] != 1 or row['boundary'] != 'post-explicit-profile' or row['pid'] != pid or row['worker_sha256'] != worker or row['helper_sha256'] != helper:
            raise ValueError('wrong host-trim installation/process/boundary')
        for key in ('allocated', 'reserved', 'pinned_owned', 'pinned_active', 'result', 'device_index', 'utc_ns'):
            if type(row[key]) is not int or row[key] < 0:
                raise ValueError('invalid host-trim counter')
        if row['fraction'] != 1.0 or row['allocated'] > row['reserved'] or row['pinned_active'] > row['pinned_owned'] or row['result'] <= 0:
            raise ValueError('invalid host-trim allocator state')
        if row['host']['MemAvailable'] < 4 * 1024**3:
            raise ValueError('host trim did not retain4GiB headroom')
    for key in ('allocated', 'reserved', 'pinned_owned', 'pinned_active', 'fraction', 'device_index', 'result'):
        if before[key] != after[key]:
            raise ValueError('host trim changed live state or original result')
    if after['utc_ns'] < before['utc_ns'] or type(after['elapsed_ns']) is not int or after['elapsed_ns'] < 0:
        raise ValueError('invalid host-trim ordering/duration')
    reclaimed = before['process']['RssAnon'] - after['process']['RssAnon']
    if after['trim_result'] != 1 or reclaimed < minimum:
        raise ValueError('host trim failed the reclamation gate')
    return dict(records=rows, reclaimed_anon_bytes=reclaimed,
                host_available_delta=after['host']['MemAvailable']-before['host']['MemAvailable'],
                pid=pid, inference_qualified=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('log', type=Path)
    parser.add_argument('--worker', required=True); parser.add_argument('--helper', required=True)
    parser.add_argument('--trace', type=Path, required=True); parser.add_argument('--minimum', type=int, default=1024**3)
    args = parser.parse_args()
    print(json.dumps(validate(args.log.read_text(), args.worker, args.helper,
                              json.loads(args.trace.read_text())['pid'], args.minimum), indent=2))
