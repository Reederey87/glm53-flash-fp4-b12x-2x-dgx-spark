"""Validate one source-bound native pinned-cache return before KV allocation."""
import argparse
import json
from pathlib import Path

MARKER = 'B12X_PINNED_RETURN '
API_SHA256 = 'ffe85913caefd73a2e2cd2866972052d926893a409f53784b348cfda9a9fc214'
HEADER_SHA256 = '9ddd1e13154fcebbb3de28bd1bb145ad82954fcff9b689c3f0d9241c09fb7e49'


def validate(log, worker, helper, trace, *, allow_physical_failure=False):
    if type(allow_physical_failure) is not bool:raise ValueError('invalid validation mode')
    rows = [json.loads(line.split(MARKER, 1)[1]) for line in log.splitlines() if MARKER in line]
    if len(rows) != 2 or [r['phase'] for r in rows] != ['before', 'after']:
        raise ValueError('need one complete pinned-cache return')
    before, after = rows
    for row in rows:
        if (row['version'] != 1 or row['boundary'] != 'post-explicit-profile' or row['pid'] != trace['pid']
                or row['worker_sha256'] != worker or row['helper_sha256'] != helper
                or row['api_sha256'] != API_SHA256 or row['header_sha256'] != HEADER_SHA256):
            raise ValueError('wrong pinned-return provider/installation/process/boundary')
        for key in ('allocated', 'reserved', 'pinned_owned', 'pinned_active', 'num_host_alloc', 'num_host_free', 'result', 'device_index', 'utc_ns'):
            if type(row[key]) is not int or row[key] < 0:
                raise ValueError('invalid pinned-return counter')
        if (row['fraction'] != 1.0 or row['allocated'] > row['reserved'] or row['pinned_active'] > row['pinned_owned']
                or not 0 < row['result'] <= 17*1024**3 or row['host']['MemAvailable'] < 4*1024**3):
            raise ValueError('invalid pinned-return admission/accounting/headroom')
    for key in ('allocated', 'reserved', 'fraction', 'num_host_alloc', 'device_index', 'result'):
        if before[key] != after[key]:
            raise ValueError('pinned return changed frozen live state/result')
    if (after['utc_ns'] < before['utc_ns'] or type(after['elapsed_ns']) is not int or after['elapsed_ns'] < 0
            or before['utc_ns'] < trace['records'][-1]['utc_ns']):
        raise ValueError('invalid pinned-return ordering/duration')
    retired_events = before['pinned_active']-after['pinned_active']
    idle_returned = before['pinned_owned']-after['pinned_owned']-retired_events
    gain = after['host']['MemAvailable']-before['host']['MemAvailable']
    if (retired_events < 0 or before['pinned_owned']-before['pinned_active'] < 256*1024**2
            or idle_returned < 256*1024**2 or after['num_host_free'] <= before['num_host_free']):
        raise ValueError('pinned return failed idle/physical reclamation gate')
    physical_pass=gain>=128*1024**2
    if not physical_pass and not allow_physical_failure:
        raise ValueError('pinned return failed idle/physical reclamation gate')
    return dict(records=rows, idle_returned_bytes=idle_returned, retired_event_bytes=retired_events,
                host_available_delta=gain, pid=trace['pid'], inference_qualified=False,
                physical_gate_passed=physical_pass)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('log', type=Path)
    parser.add_argument('--worker', required=True); parser.add_argument('--helper', required=True)
    parser.add_argument('--trace', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(validate(args.log.read_text(), args.worker, args.helper,
                              json.loads(args.trace.read_text())), indent=2))
