"""Validate a terminal ownership diagnostic; never declares serving qualified."""
import argparse
import json
from pathlib import Path

MARKER = 'B12X_HOST_OWNERSHIP '


def validate(log, worker, helper, pid):
    rows = [json.loads(line.split(MARKER, 1)[1]) for line in log.splitlines() if MARKER in line]
    if len(rows) != 1:
        raise ValueError('need exactly one complete ownership record')
    row = rows[0]
    if row['version'] != 1 or row['pid'] != pid or row['worker_sha256'] != worker or row['helper_sha256'] != helper:
        raise ValueError('wrong ownership process or installed hashes')
    for key in ('allocated', 'reserved', 'cuda_free', 'cuda_total', 'pid', 'ppid', 'utc_ns', 'device_index'):
        if type(row[key]) is not int or row[key] < 0:
            raise ValueError('invalid ownership counter ' + key)
    if row['fraction'] != 1.0 or row['allocated'] > row['reserved'] or row['cuda_free'] > row['cuda_total']:
        raise ValueError('inconsistent allocator counters')
    pinned = row['pinned']
    for value in pinned.values():
        if type(value) is not int or value < 0:
            raise ValueError('invalid host allocator counter')
    if pinned['active_bytes.current'] > pinned['allocated_bytes.current']:
        raise ValueError('active pinned bytes exceed ownership')
    if row['host']['MemAvailable'] < 2 * 1024**3:
        raise ValueError('ownership diagnostic crossed host floor')
    pids = [p['pid'] for p in row['processes']]
    if len(pids) > 8 or len(set(pids)) != len(pids) or pid not in pids:
        raise ValueError('invalid process coverage')
    return dict(record=row, pinned_inactive_bytes=pinned['allocated_bytes.current']-pinned['active_bytes.current'],
                serving_qualified=False, planned_terminal_diagnostic=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('log', type=Path)
    parser.add_argument('--worker', required=True)
    parser.add_argument('--helper', required=True)
    parser.add_argument('--trace', type=Path, required=True)
    args = parser.parse_args()
    trace = json.loads(args.trace.read_text())
    print(json.dumps(validate(args.log.read_text(), args.worker, args.helper, trace['pid']), indent=2))
