"""Terminal native-owner inventory after successful common pinned return."""
import base64
from functools import wraps
import gc
import hashlib
import json
import os
from pathlib import Path
import time

from vllm.v1.worker._b12x_native_metadata import collect, providers, PROVIDERS

MARKER = 'B12X_HOST_OWNERSHIP '
CHUNK_MARKER = 'B12X_NATIVE_OWNERS '
BOUNDARY = 'post-profile-pinned-before-KV'
PINNED_SHA = '1761e9aeb863da2cb307fc7094c30af495aa78ff9e135e9d58d81df7b6c82ac6'
ENTRY_FLOOR = 10 * 1024**3


def fields(path, keys):
    result = {}
    for line in Path(path).read_text().splitlines():
        name, _, value = line.partition(':')
        if name in keys:
            result[name] = int(value.split()[0]) * 1024
    if set(result) != set(keys):
        raise ValueError('missing process/host memory fields')
    return result


def snapshot(torch, device):
    processes = []
    for pid in dict.fromkeys((os.getpid(), os.getppid())):
        processes.append(dict(pid=pid, **fields(f'/proc/{pid}/status', ('VmRSS', 'RssAnon')),
            pss=fields(f'/proc/{pid}/smaps_rollup', ('Pss', 'Pss_Anon', 'Pss_File', 'Pss_Shmem'))))
    free, total = torch.cuda.mem_get_info(device)
    stats = torch.cuda.memory.host_memory_stats()
    return dict(pid=os.getpid(), ppid=os.getppid(), utc_ns=time.time_ns(), device_index=device,
        fraction=torch.cuda.memory.get_per_process_memory_fraction(device),
        allocated=torch.cuda.memory_allocated(device), reserved=torch.cuda.memory_reserved(device),
        cuda_free=free, cuda_total=total,
        pinned={key: stats[key] for key in ('allocated_bytes.current', 'active_bytes.current', 'num_host_alloc', 'num_host_free')},
        processes=processes, process_coverage='self-parent',
        host=fields('/proc/meminfo', ('MemFree', 'MemAvailable')),
        gc_enabled=gc.isenabled(), frozen_objects=gc.get_freeze_count())


def emit(marker, record):
    data = (marker + json.dumps(record, separators=(',', ':')) + '\n').encode()
    if len(data) > 4096 or os.write(2, data) != len(data):
        raise RuntimeError('invalid bounded native-owner receipt write')


def terminal_hold():
    while True:
        time.sleep(60)


def observe_native_owners_terminal(function):
    @wraps(function)
    def wrapped(worker, *args, **kwargs):
        data = object.__getattribute__(worker, '__dict__')
        if data.get('_b12x_native_owners_seen', False):
            raise RuntimeError('native ownership is startup-once')
        data['_b12x_native_owners_seen'] = True
        if worker.cache_config.kv_cache_memory_bytes != 17 * 1024**3:
            raise RuntimeError('native ownership requires frozen explicit17G')
        result = function(worker, *args, **kwargs)
        if type(result) is not int or not 0 < result <= 17 * 1024**3:
            raise RuntimeError('invalid original KV admission result')
        for key, expected in (('_b12x_startup_coordinator', None), ('_b12x_stage', None),
                              ('_b12x_profile_batch', None), ('_b12x_tuning_cache', False),
                              ('_b12x_pinned_return_done', True)):
            if key not in data or data[key] is not expected:
                raise RuntimeError('profile preparation not completed: ' + key)
        import torch
        from vllm.platforms import current_platform
        if worker.device.type != 'cuda' or not torch.cuda.is_initialized():
            raise RuntimeError('native ownership requires initialized CUDA')
        device = worker.device.index
        if device is None:
            device = torch.cuda.current_device()
        if (not current_platform.is_integrated_gpu(device) or torch.cuda.memory.get_allocator_backend() != 'native'
                or torch.cuda.is_current_stream_capturing() or torch.cuda.memory.get_per_process_memory_fraction(device) != 1.0):
            raise RuntimeError('requires integrated/native restored CUDA outside capture')
        helper = Path(__file__)
        if hashlib.sha256(helper.with_name('_b12x_startup_pinned.py').read_bytes()).hexdigest() != PINNED_SHA:
            raise RuntimeError('common pinned helper differs from reviewed source')
        plan, classes = providers()
        before = snapshot(torch, device)
        if before['host']['MemAvailable'] < ENTRY_FLOOR:
            raise RuntimeError('native inventory requires fresh10GiB entry headroom')
        report = collect(plan, classes)
        after = snapshot(torch, device)
        for key in ('allocated', 'reserved', 'fraction', 'pinned', 'gc_enabled', 'frozen_objects'):
            if before[key] != after[key]:
                raise RuntimeError('inventory changed frozen live state: ' + key)
        before_self = before['processes'][0]; after_self = after['processes'][0]
        if after['host']['MemAvailable'] < ENTRY_FLOOR or after_self['RssAnon'] - before_self['RssAnon'] > 64 * 1024**2:
            raise RuntimeError('inventory exceeded host/64MiB anonymous growth budget')
        raw = json.dumps(report, separators=(',', ':')).encode()
        digest = hashlib.sha256(raw).hexdigest()
        encoded = base64.b64encode(raw).decode('ascii')
        count = (len(encoded) + 2999) // 3000
        if not 0 < count <= 512:
            raise RuntimeError('native inventory chunk limit exceeded')
        for index in range(count):
            emit(CHUNK_MARKER, dict(pid=after['pid'], index=index, count=count,
                sha256=digest, data=encoded[index * 3000:(index + 1) * 3000]))
        emit(MARKER, dict(after, version=1, boundary=BOUNDARY, result=result,
            before=before, inventory_sha256=digest, inventory_chunks=count,
            metadata_sha256=hashlib.sha256(helper.with_name('_b12x_native_metadata.py').read_bytes()).hexdigest(),
            helper_sha256=hashlib.sha256(helper.read_bytes()).hexdigest(),
            worker_sha256=hashlib.sha256(helper.with_name('gpu_worker.py').read_bytes()).hexdigest(),
            providers=PROVIDERS, pinned_helper_sha256=PINNED_SHA,
            profile_completed=True, inventory_complete=report['complete']))
        terminal_hold()
        raise RuntimeError('terminal native ownership unexpectedly returned')
    return wrapped
