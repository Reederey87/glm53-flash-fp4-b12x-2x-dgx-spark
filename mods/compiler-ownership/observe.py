"""Measure retained compiler ownership after profiling, then stop before KV."""
from functools import wraps
import hashlib
import json
import os
from pathlib import Path
import time

from vllm.v1.worker._b12x_compiler_metadata import compiler_summary, mapping_summary

MARKER = 'B12X_HOST_OWNERSHIP '
STATUS_KEYS = ('VmRSS', 'RssAnon', 'RssFile', 'RssShmem', 'VmLck', 'VmPin')
HOST_KEYS = ('MemTotal', 'MemFree', 'MemAvailable', 'Cached', 'AnonPages',
             'Shmem', 'Slab', 'SReclaimable', 'SUnreclaim', 'PageTables', 'Unevictable', 'Mlocked')


def byte_fields(path, keys):
    result = {}
    for line in Path(path).read_text().splitlines():
        name, _, value = line.partition(':')
        if name in keys:
            result[name] = int(value.split()[0]) * 1024
    return result


def process_memory():
    """Bounded container-PID view; RSS/PSS are separate and never added to CUDA."""
    rows = []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            data = byte_fields(entry / 'status', STATUS_KEYS)
            data['pid'] = int(entry.name)
            rows.append(data)
        except (OSError, ValueError):
            continue
    rows.sort(key=lambda r: r.get('VmRSS', 0), reverse=True)
    chosen = rows[:6]
    for row in rows:
        if row['pid'] in (os.getpid(), os.getppid()) and row not in chosen:
            chosen.append(row)
    for row in chosen:
        try:
            row['pss'] = byte_fields(f"/proc/{row['pid']}/smaps_rollup",
                                     ('Pss', 'Pss_Anon', 'Pss_File', 'Pss_Shmem', 'Private_Dirty'))
        except (OSError, ValueError) as error:
            row['pss_error'] = type(error).__name__
    return chosen


def snapshot(worker):
    import torch
    from vllm.platforms import current_platform
    if worker.device.type != 'cuda' or not torch.cuda.is_initialized():
        raise RuntimeError('ownership diagnostic requires initialized CUDA')
    device = worker.device.index
    if device is None:
        device = torch.cuda.current_device()
    if not current_platform.is_integrated_gpu(device):
        raise RuntimeError('ownership diagnostic requires integrated GPU')
    if torch.cuda.is_current_stream_capturing():
        raise RuntimeError('ownership diagnostic cannot run inside capture')
    if torch.cuda.memory.get_allocator_backend() != 'native':
        raise RuntimeError('ownership diagnostic requires native allocator')
    fraction = torch.cuda.memory.get_per_process_memory_fraction(device)
    if fraction != 1.0:
        raise RuntimeError('postload fraction not restored')
    stats = torch.cuda.memory.host_memory_stats()
    pinned = {key: stats[key] for key in ('allocated_bytes.current', 'active_bytes.current', 'num_host_alloc', 'num_host_free')}
    free, total = torch.cuda.mem_get_info(device)
    helper = Path(__file__)
    return dict(version=1, boundary='post-explicit-profile', pid=os.getpid(), ppid=os.getppid(), utc_ns=time.time_ns(),
                device_index=device, fraction=fraction,
                allocated=torch.cuda.memory_allocated(device), reserved=torch.cuda.memory_reserved(device),
                cuda_free=free, cuda_total=total, pinned=pinned,
                processes=process_memory(), host=byte_fields('/proc/meminfo', HOST_KEYS),
                worker_sha256=hashlib.sha256(helper.with_name('gpu_worker.py').read_bytes()).hexdigest(),
                helper_sha256=hashlib.sha256(helper.read_bytes()).hexdigest(),
                metadata_sha256=hashlib.sha256(helper.with_name('_b12x_compiler_metadata.py').read_bytes()).hexdigest())


def emit(marker, record):
    data = (marker + json.dumps(record, separators=(',', ':')) + '\n').encode()
    if len(data) > 4096 or os.write(2, data) != len(data):
        raise RuntimeError('invalid compiler ownership record write')


def observe_compiler_ownership(function):
    @wraps(function)
    def wrapped(worker, *args, **kwargs):
        if worker.cache_config.kv_cache_memory_bytes != 17 * 1024**3:
            raise RuntimeError('compiler diagnostic requires frozen explicit17G')
        result = function(worker, *args, **kwargs)
        if type(result) is not int or result <= 0:
            raise RuntimeError('invalid original admission result')
        before = snapshot(worker)
        own_process = next(row for row in before['processes'] if row['pid'] == before['pid'])
        if before['host']['MemAvailable'] < 8 * 1024**3 or own_process['VmRSS'] > 8 * 1024**3:
            raise RuntimeError('compiler diagnostic requires8GiB free and bounded workerRSS before collection')
        objects = compiler_summary()
        with open('/proc/self/smaps') as source:
            mappings = mapping_summary(source)
        after = snapshot(worker)
        for key in ('allocated', 'reserved', 'pinned', 'fraction'):
            if before[key] != after[key]:
                raise RuntimeError('compiler diagnostic changed live allocator counters')
        common = {key:after[key] for key in ('version','boundary','pid','utc_ns','worker_sha256','helper_sha256','metadata_sha256')}
        emit('B12X_COMPILER_OBJECTS ', dict(common, objects=objects))
        emit('B12X_COMPILER_MAPS ', dict(common, mappings=mappings))
        # Primary record LAST is the supervisor's complete-record readiness marker.
        emit(MARKER, dict(after, result=result))
        # Never return into KV allocation. Stop-only supervisor owns both ranks;
        # finite fallback is terminal even if it disappears.
        time.sleep(120)
        raise RuntimeError('B12X compiler ownership intentional terminal stop')
    return wrapped
