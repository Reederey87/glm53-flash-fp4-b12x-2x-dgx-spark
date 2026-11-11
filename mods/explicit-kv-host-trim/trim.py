"""Return unused glibc pages after explicit-KV profiling, before pool allocation."""
import ctypes
from functools import wraps
import hashlib
import json
import os
from pathlib import Path
import time

MINIMUM_RECLAIM = 1024**3
MARKER = 'B12X_HOST_TRIM '


def fields(path, keys):
    result = {}
    for line in Path(path).read_text().splitlines():
        key, _, value = line.partition(':')
        if key in keys:
            result[key] = int(value.split()[0]) * 1024
    return result


def snapshot(torch, device, result, phase):
    helper = Path(__file__)
    pinned = torch.cuda.memory.host_memory_stats()
    return dict(version=1, phase=phase, boundary='post-explicit-profile', pid=os.getpid(), utc_ns=time.time_ns(),
                device_index=device, result=result, fraction=torch.cuda.memory.get_per_process_memory_fraction(device),
                allocated=torch.cuda.memory_allocated(device), reserved=torch.cuda.memory_reserved(device),
                pinned_owned=pinned['allocated_bytes.current'], pinned_active=pinned['active_bytes.current'],
                process=fields('/proc/self/status', ('VmRSS', 'RssAnon')),
                host=fields('/proc/meminfo', ('MemFree', 'MemAvailable')),
                worker_sha256=hashlib.sha256(helper.with_name('gpu_worker.py').read_bytes()).hexdigest(),
                helper_sha256=hashlib.sha256(helper.read_bytes()).hexdigest())


def emit(record):
    data = (MARKER + json.dumps(record, separators=(',', ':')) + '\n').encode()
    if len(data) > 4096 or os.write(2, data) != len(data):
        raise RuntimeError('invalid host-trim receipt write')


def trim_after_explicit_profile(function):
    @wraps(function)
    def wrapped(worker, *args, **kwargs):
        import torch
        from vllm.platforms import current_platform
        if worker.cache_config.kv_cache_memory_bytes != 17 * 1024**3:
            raise RuntimeError('host trim requires the frozen explicit17G KV request')
        result = function(worker, *args, **kwargs)
        if type(result) is not int or result <= 0:
            raise RuntimeError('invalid original KV admission result')
        if worker.device.type != 'cuda' or not torch.cuda.is_initialized():
            raise RuntimeError('host trim requires initialized CUDA')
        device = worker.device.index
        if device is None:
            device = torch.cuda.current_device()
        if not current_platform.is_integrated_gpu(device) or torch.cuda.memory.get_allocator_backend() != 'native':
            raise RuntimeError('host trim requires integrated/native CUDA')
        if torch.cuda.is_current_stream_capturing() or torch.cuda.memory.get_per_process_memory_fraction(device) != 1.0:
            raise RuntimeError('host trim requires restored fraction outside capture')
        trim = ctypes.CDLL(None).malloc_trim
        trim.argtypes = (ctypes.c_size_t,)
        trim.restype = ctypes.c_int
        before = snapshot(torch, device, result, 'before')
        emit(before)
        if before['host']['MemAvailable'] < 4 * 1024**3:
            raise RuntimeError('insufficient host headroom before trim')
        started = time.monotonic_ns()
        returned = trim(0)
        after = snapshot(torch, device, result, 'after')
        after.update(trim_result=returned, elapsed_ns=time.monotonic_ns()-started)
        emit(after)
        for key in ('allocated', 'reserved', 'pinned_owned', 'pinned_active', 'fraction'):
            if before[key] != after[key]:
                raise RuntimeError('host trim changed live allocator accounting: ' + key)
        if after['host']['MemAvailable'] < 4 * 1024**3:
            raise RuntimeError('insufficient host headroom after trim')
        if returned != 1 or before['process']['RssAnon']-after['process']['RssAnon'] < MINIMUM_RECLAIM:
            raise RuntimeError('host trim reclaimed less than the required1GiB; refuse KV allocation')
        return result
    return wrapped
