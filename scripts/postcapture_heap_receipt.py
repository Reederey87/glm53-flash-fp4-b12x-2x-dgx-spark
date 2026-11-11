"""Require source-bound post-capture free-heap evidence and physical return."""
import argparse
import json
from pathlib import Path

MARKER = 'B12X_POSTCAPTURE_HEAP '
PROVIDERS = dict(plan_sha256='272ddb4f674b437e185e6c52274d87333534e0100db29ff5cf88a2e2fefc3e24',
                 gc_sha256='e31de173771f6f3eaef4f12a5ec1da3a71f3e1b80aed2bbedd223a86228829d1',
                 workspace_sha256='18334e399b5d7749a0733d64fe6214906d0f9d276fc7c65806603de4c912449c',
                 graph_sha256='d43c261320ab63558b0975d9265e6ffe4871512bf7f4a448cfa81a8e6821f971')


def validate_observation(log, runner, helper, trace):
    rows = [json.loads(s.split(MARKER,1)[1]) for s in log.splitlines() if MARKER in s]
    if len(rows)!=1 or rows[0]['phase']!='observe':
        raise ValueError('need exactly one terminal postcapture observation')
    row=rows[0]
    if (row['version']!=1 or row['boundary']!='post-capture-before-second-warmup' or row['pid']!=trace['pid']
            or row['runner_sha256']!=runner or row['helper_sha256']!=helper
            or any(row.get(k)!=v for k,v in PROVIDERS.items())):
        raise ValueError('wrong terminal observation installation/provider/process')
    if not 0 <= log.find('Graph capturing finished') < log.find(MARKER):
        raise ValueError('terminal observation did not follow completed capture')
    if row['utc_ns'] < trace['records'][-1]['utc_ns']:
        raise ValueError('terminal observation precedes postload')
    for key in ('allocated','reserved','pinned_owned','pinned_active','device_index','frozen_objects','retained_program_owners','utc_ns'):
        if type(row[key]) is not int or row[key]<0:raise ValueError('invalid terminal counter')
    if (row['fraction']!=1. or row['graphs_captured'] is not True or row['workspace_locked'] is not True
            or row['kv_bytes']!=17*1024**3 or type(row['result']) is not int or type(row['gc_enabled']) is not bool
            or not 0<row['retained_program_owners']<=4096 or row['allocated']>row['reserved']
            or row['pinned_active']>row['pinned_owned'] or row['host']['MemAvailable']<2*1024**3):
        raise ValueError('invalid/unsafe terminal postcapture state')
    heap=row['heap']
    if (any(type(heap[k]) is not int or heap[k]<0 for k in ('arenas','free_chunk_bytes','system_current_bytes','mmap_bytes'))
            or not heap['arenas'] or heap['free_chunk_bytes']>heap['system_current_bytes']):
        raise ValueError('invalid terminal all-arena observation')
    for name,keys in ((row['process'],('RssAnon','VmRSS')),(row['pss'],('Rss','Pss_Anon','Anonymous','Private_Dirty','Shared_Dirty','AnonHugePages','Swap','SwapPss'))):
        if any(type(name[k]) is not int or name[k]<0 for k in keys):raise ValueError('invalid terminal process/PSS accounting')
    return dict(record=row,terminal_observation=True,cleanup_performed=False,inference_qualified=False)


def validate(log, runner, helper, trace):
    rows = [json.loads(line.split(MARKER, 1)[1]) for line in log.splitlines() if MARKER in line]
    if len(rows) != 2 or [r['phase'] for r in rows] != ['before', 'after']:
        raise ValueError('need one complete postcapture return')
    if not 0 <= log.find('Graph capturing finished') < log.find(MARKER):
        raise ValueError('capture-completion evidence missing or reordered')
    before, after = rows
    for row in rows:
        if (row['version'] != 1 or row['boundary'] != 'post-capture-before-second-warmup' or row['pid'] != trace['pid']
                or row['runner_sha256'] != runner or row['helper_sha256'] != helper
                or any(row.get(k) != v for k, v in PROVIDERS.items())):
            raise ValueError('wrong postcapture provider/installation/process/boundary')
        for key in ('device_index', 'allocated', 'reserved', 'pinned_owned', 'pinned_active', 'utc_ns', 'retained_program_owners', 'frozen_objects'):
            if type(row[key]) is not int or row[key] < 0:
                raise ValueError('invalid postcapture counter')
        if (type(row['result']) is not int or row['kv_bytes'] != 17*1024**3 or row['fraction'] != 1.
                or row['allocated'] > row['reserved'] or row['pinned_active'] > row['pinned_owned']
                or row['workspace_locked'] is not True or row['graphs_captured'] is not True or type(row['gc_enabled']) is not bool
                or not 0 < row['retained_program_owners'] <= 4096 or row['host']['MemAvailable'] < 2*1024**3):
            raise ValueError('invalid postcapture accounting/ownership/floor')
        if type(row['process']['RssAnon']) is not int or row['process']['RssAnon'] < 0:
            raise ValueError('invalid postcapture RSS')
        heap = row['heap']
        if (any(type(heap[k]) is not int or heap[k] < 0 for k in ('arenas', 'free_chunk_bytes', 'system_current_bytes', 'mmap_bytes'))
                or heap['arenas'] < 1 or heap['free_chunk_bytes'] > heap['system_current_bytes']):
            raise ValueError('invalid all-arena heap observation')
    for key in ('device_index', 'result', 'kv_bytes', 'fraction', 'allocated', 'reserved', 'pinned_owned', 'pinned_active',
                'workspace_locked', 'gc_enabled', 'frozen_objects', 'retained_program_owners', 'retained_identity_sha256'):
        if before[key] != after[key]:
            raise ValueError('postcapture return changed live state/result')
    if (after['utc_ns'] < before['utc_ns'] or before['utc_ns'] < trace['records'][-1]['utc_ns']
            or type(after['elapsed_ns']) is not int or after['elapsed_ns'] < 0):
        raise ValueError('invalid postcapture order/duration')
    returned = before['process']['RssAnon']-after['process']['RssAnon']
    gain = after['host']['MemAvailable']-before['host']['MemAvailable']
    if (before['heap']['free_chunk_bytes'] < 256*1024**2 or after['trim_result'] != 1
            or returned < 256*1024**2 or gain < 128*1024**2):
        raise ValueError('postcapture return failed free-heap/physical gate')
    return dict(records=rows, reclaimed_anon_bytes=returned, host_available_delta=gain,
                pid=trace['pid'], inference_qualified=False)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('log', type=Path)
    p.add_argument('--runner', required=True); p.add_argument('--helper', required=True)
    p.add_argument('--trace', type=Path, required=True); p.add_argument('--observe',action='store_true'); a = p.parse_args()
    fn=validate_observation if a.observe else validate
    print(json.dumps(fn(a.log.read_text(), a.runner, a.helper, json.loads(a.trace.read_text())), indent=2))
