"""Retire compiler lookup ownership before KV; preserve retained launch programs."""
import ctypes
import importlib
from functools import wraps
import hashlib
import json
import os
from pathlib import Path
import time

MINIMUM_RECLAIM = 1024**3
MARKER = 'B12X_COMPILER_RELEASE '
COMPILER_SHA = '3a73fe9d56fe1bf6277b92f8ec7c28b9b0a7b6c02e1ca2c04106c9922e83694b'
PLAN_SHA = '272ddb4f674b437e185e6c52274d87333534e0100db29ff5cf88a2e2fefc3e24'


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


def providers():
    compiler = importlib.import_module('b12x._lib.compiler')
    plan = importlib.import_module('b12x._lib.compile_plan')
    paths = (Path(compiler.__file__).resolve(), Path(plan.__file__).resolve())
    hashes = tuple(hashlib.sha256(path.read_bytes()).hexdigest() for path in paths)
    if hashes != (COMPILER_SHA, PLAN_SHA):
        raise RuntimeError('compiler ownership provider differs from pinned source')
    return compiler, plan, dict(compiler_sha256=hashes[0], plan_sha256=hashes[1], compiler_provider=str(paths[0]))


def retention(plan):
    identities = set()
    # Only integers/program hashes escape this frame; do not retain extra
    # executable references across eviction and bias the reclamation result.
    for retained in tuple(plan._LIVE_RETAINED_PROGRAMS):
        for owner in retained.owners.values():
            for program in plan.program_keys(owner):
                identities.add((program.dialect, program.key, id(owner)))
                if len(identities) > 4096:
                    raise RuntimeError('too many retained launch owners for reviewed window')
    return dict(retained_program_owners=len(identities), retained_identity_sha256=
                hashlib.sha256(json.dumps(sorted(identities),separators=(',',':')).encode()).hexdigest())


def release_after_explicit_profile(function):
    @wraps(function)
    def wrapped(worker, *args, **kwargs):
        if getattr(worker,'_b12x_compiler_release_seen',False):
            raise RuntimeError('compiler lookup release is startup-once only')
        import torch
        from vllm.platforms import current_platform
        if worker.cache_config.kv_cache_memory_bytes != 17 * 1024**3:
            raise RuntimeError('compiler release requires frozen explicit17G KV')
        result = function(worker, *args, **kwargs)
        if type(result) is not int or result <= 0:
            raise RuntimeError('invalid original KV admission result')
        if worker.device.type != 'cuda' or not torch.cuda.is_initialized():
            raise RuntimeError('compiler release requires initialized CUDA')
        device = worker.device.index
        if device is None: device = torch.cuda.current_device()
        if not current_platform.is_integrated_gpu(device) or torch.cuda.memory.get_allocator_backend() != 'native':
            raise RuntimeError('compiler release requires integrated/native CUDA')
        if torch.cuda.is_current_stream_capturing() or torch.cuda.memory.get_per_process_memory_fraction(device) != 1.0:
            raise RuntimeError('compiler release requires restored fraction outside capture')
        compiler, plan, source = providers()
        if plan._RETAINED_PROGRAMS.get() is not None or getattr(worker,'_b12x_startup_coordinator',None) is not None or getattr(worker,'_b12x_profile_batch',None) is not None:
            raise RuntimeError('cannot retire compiler lookups during active preparation')
        worker._b12x_compiler_release_seen=True
        trim = ctypes.CDLL(None).malloc_trim
        trim.argtypes = (ctypes.c_size_t,); trim.restype = ctypes.c_int
        before = snapshot(torch,device,result,'before')
        before.update(source, **retention(plan), cache=compiler.compile_cache_info())
        emit(before)
        if before['host']['MemAvailable'] < 4*1024**3:
            raise RuntimeError('insufficient headroom before compiler release')
        if before['cache']['memory_cache_size'] + before['cache']['spec_memo_size'] == 0:
            raise RuntimeError('no compiler lookup ownership to retire')
        started = time.monotonic_ns()
        compiler.clear_compile_cache()
        returned = trim(0)
        after = snapshot(torch,device,result,'after')
        after.update(source, **retention(plan), cache=compiler.compile_cache_info(),
                     trim_result=returned,elapsed_ns=time.monotonic_ns()-started)
        emit(after)
        for key in ('allocated','reserved','pinned_owned','pinned_active','fraction','retained_program_owners','retained_identity_sha256'):
            if before[key] != after[key]:
                raise RuntimeError('compiler release changed live ownership: '+key)
        if after['cache']['memory_cache_size'] != 0 or after['cache']['spec_memo_size'] != 0:
            raise RuntimeError('compiler lookup eviction not complete')
        if after['host']['MemAvailable'] < 4*1024**3:
            raise RuntimeError('insufficient headroom after compiler release')
        if before['process']['RssAnon']-after['process']['RssAnon'] < MINIMUM_RECLAIM:
            raise RuntimeError('compiler release reclaimed less than1GiB; refuse KV allocation')
        return result
    return wrapped
