"""Read ownership counters at warmup entry, then stop before invoking warmup."""
from functools import wraps
import hashlib
import json
import os
from pathlib import Path
import time

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
    return dict(version=1, boundary='pre-warmup', pid=os.getpid(), ppid=os.getppid(), utc_ns=time.time_ns(),
                device_index=device, fraction=fraction,
                allocated=torch.cuda.memory_allocated(device), reserved=torch.cuda.memory_reserved(device),
                cuda_free=free, cuda_total=total, pinned=pinned,
                processes=process_memory(), host=byte_fields('/proc/meminfo', HOST_KEYS),
                worker_sha256=hashlib.sha256(helper.with_name('gpu_worker.py').read_bytes()).hexdigest(),
                helper_sha256=hashlib.sha256(helper.read_bytes()).hexdigest())


def observe_before_warmup(function):
    @wraps(function)
    def wrapped(worker, *args, **kwargs):
        data = (MARKER + json.dumps(snapshot(worker), separators=(',', ':')) + '\n').encode()
        if len(data) > 4096:
            raise RuntimeError('ownership record exceeds atomic log limit')
        if os.write(2, data) != len(data):
            raise RuntimeError('incomplete ownership record')
        # Never invoke the original warmup or return to the executor. The supervised window
        # stops both ranks once both records arrive. A finite fallback prevents
        # a forgotten diagnostic from holding forever if its supervisor dies.
        time.sleep(120)
        raise RuntimeError('B12X ownership diagnostic intentional terminal stop')
    return wrapped
