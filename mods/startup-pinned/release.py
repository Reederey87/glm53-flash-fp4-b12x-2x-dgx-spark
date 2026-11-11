"""Return idle pinned host blocks at the synchronized explicit-KV boundary."""
from functools import wraps
import hashlib
import json
import os
from pathlib import Path
import time

MARKER = 'B12X_PINNED_RETURN '
MINIMUM_IDLE_RETURN = 256 * 1024**2
MINIMUM_AVAILABLE_GAIN = 128 * 1024**2
API_SHA256 = 'ffe85913caefd73a2e2cd2866972052d926893a409f53784b348cfda9a9fc214'
HEADER_SHA256 = '9ddd1e13154fcebbb3de28bd1bb145ad82954fcff9b689c3f0d9241c09fb7e49'


def fields(path, keys):
    result = {}
    for line in Path(path).read_text().splitlines():
        key, _, value = line.partition(':')
        if key in keys:
            result[key] = int(value.split()[0]) * 1024
    return result


def provider(torch):
    api = Path(torch.accelerator.memory.__file__)
    header = Path(torch.__file__).parent/'include/ATen/core/CachingHostAllocator.h'
    hashes = dict(api_sha256=hashlib.sha256(api.read_bytes()).hexdigest(),
                  header_sha256=hashlib.sha256(header.read_bytes()).hexdigest())
    if hashes != dict(api_sha256=API_SHA256, header_sha256=HEADER_SHA256):
        raise RuntimeError('pinned host allocator provider differs from reviewed image')
    if not callable(getattr(torch.accelerator.memory, 'empty_host_cache', None)):
        raise RuntimeError('public pinned host-cache API missing')
    return hashes


def snapshot(torch, device, result, phase, hashes):
    helper = Path(__file__)
    pinned = torch.cuda.memory.host_memory_stats()
    return dict(version=1, phase=phase, boundary='post-explicit-profile', pid=os.getpid(), utc_ns=time.time_ns(),
                device_index=device, result=result, fraction=torch.cuda.memory.get_per_process_memory_fraction(device),
                allocated=torch.cuda.memory_allocated(device), reserved=torch.cuda.memory_reserved(device),
                pinned_owned=pinned['allocated_bytes.current'], pinned_active=pinned['active_bytes.current'],
                num_host_alloc=pinned['num_host_alloc'], num_host_free=pinned['num_host_free'],
                host=fields('/proc/meminfo', ('MemFree', 'MemAvailable')),
                worker_sha256=hashlib.sha256(helper.with_name('gpu_worker.py').read_bytes()).hexdigest(),
                helper_sha256=hashlib.sha256(helper.read_bytes()).hexdigest(), **hashes)


def emit(record):
    data = (MARKER + json.dumps(record, separators=(',', ':')) + '\n').encode()
    if len(data) > 4096 or os.write(2, data) != len(data):
        raise RuntimeError('invalid pinned-return receipt write')


def release_after_explicit_profile(function):
    @wraps(function)
    def wrapped(worker, *args, **kwargs):
        import torch
        from vllm.platforms import current_platform
        if worker.cache_config.kv_cache_memory_bytes != 17 * 1024**3:
            raise RuntimeError('pinned return requires frozen explicit17G KV request')
        if getattr(worker, '_b12x_pinned_return_done', False):
            raise RuntimeError('pinned return is startup-once')
        worker._b12x_pinned_return_done = True
        result = function(worker, *args, **kwargs)
        if type(result) is not int or not 0 < result <= 17*1024**3:
            raise RuntimeError('invalid original KV admission result')
        if (getattr(worker, '_b12x_startup_coordinator', None) is not None
                or getattr(worker, '_b12x_profile_batch', None) is not None):
            raise RuntimeError('profiling preparation still active')
        if worker.device.type != 'cuda' or not torch.cuda.is_initialized():
            raise RuntimeError('pinned return requires initialized CUDA')
        device = worker.device.index
        if device is None:
            device = torch.cuda.current_device()
        if not current_platform.is_integrated_gpu(device) or torch.cuda.memory.get_allocator_backend() != 'native':
            raise RuntimeError('pinned return requires integrated/native CUDA')
        if torch.cuda.is_current_stream_capturing() or torch.cuda.memory.get_per_process_memory_fraction(device) != 1.0:
            raise RuntimeError('pinned return requires restored fraction outside capture')
        hashes = provider(torch)
        before = snapshot(torch, device, result, 'before', hashes)
        emit(before)
        if before['host']['MemAvailable'] < 4 * 1024**3:
            raise RuntimeError('insufficient host headroom before pinned return')
        if before['pinned_owned']-before['pinned_active'] < MINIMUM_IDLE_RETURN:
            raise RuntimeError('insufficient measured idle pinned memory; refuse KV allocation')
        started = time.monotonic_ns()
        torch.accelerator.memory.empty_host_cache()
        after = snapshot(torch, device, result, 'after', hashes)
        after['elapsed_ns'] = time.monotonic_ns()-started
        emit(after)
        for key in ('allocated', 'reserved', 'fraction', 'num_host_alloc'):
            if before[key] != after[key]:
                raise RuntimeError('pinned return changed frozen live state: '+key)
        retired_events = before['pinned_active']-after['pinned_active']
        idle_returned = before['pinned_owned']-after['pinned_owned']-retired_events
        if (retired_events < 0 or idle_returned < MINIMUM_IDLE_RETURN
                or after['num_host_free'] <= before['num_host_free']):
            raise RuntimeError('pinned cache failed idle256MiB return gate; refuse KV allocation')
        if (after['host']['MemAvailable'] < 4 * 1024**3
                or after['host']['MemAvailable']-before['host']['MemAvailable'] < MINIMUM_AVAILABLE_GAIN):
            raise RuntimeError('pinned cache failed physical128MiB return gate; refuse KV allocation')
        return result
    return wrapped
