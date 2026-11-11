"""Measure and return unused glibc pages after capture's existing collection."""
import ctypes
from functools import wraps
import gc
import hashlib
import importlib
import json
import os
from pathlib import Path
import time
import xml.etree.ElementTree as ET

MARKER = 'B12X_POSTCAPTURE_HEAP '
MINIMUM_RETURN = 256 * 1024**2
MINIMUM_AVAILABLE_GAIN = 128 * 1024**2
FLOOR = 2 * 1024**3
PLAN_SHA = '272ddb4f674b437e185e6c52274d87333534e0100db29ff5cf88a2e2fefc3e24'
GC_SHA = 'e31de173771f6f3eaef4f12a5ec1da3a71f3e1b80aed2bbedd223a86228829d1'
WORKSPACE_SHA = '18334e399b5d7749a0733d64fe6214906d0f9d276fc7c65806603de4c912449c'
GRAPH_SHA = 'd43c261320ab63558b0975d9265e6ffe4871512bf7f4a448cfa81a8e6821f971'
HEAP_REPORT_BYTES = 128 * 1024


def fields(path, keys):
    result = {}
    for line in Path(path).read_text().splitlines():
        key, _, value = line.partition(':')
        if key in keys:
            result[key] = int(value.split()[0]) * 1024
    return result


def parse_heap(data):
    root = ET.fromstring(data)
    if root.tag != 'malloc' or root.get('version') != '1' or not root.findall('heap'):
        raise ValueError('unexpected malloc_info format')
    def one(tag, kind):
        rows = root.findall(f"{tag}[@type='{kind}']")
        if len(rows) != 1:
            raise ValueError('missing/duplicate aggregate malloc_info field')
        number = int(rows[0].attrib['size'])
        if number < 0:
            raise ValueError('negative malloc_info size')
        return number
    free = one('total', 'fast') + one('total', 'rest')
    current = one('system', 'current')
    if current < free:
        raise ValueError('inconsistent malloc_info aggregate')
    return dict(arenas=len(root.findall('heap')), free_chunk_bytes=free,
                system_current_bytes=current, mmap_bytes=one('total', 'mmap'))


def libc_api():
    libc = ctypes.CDLL(None)
    libc.fmemopen.argtypes = (ctypes.c_void_p, ctypes.c_size_t, ctypes.c_char_p)
    libc.fmemopen.restype = ctypes.c_void_p
    libc.malloc_info.argtypes = (ctypes.c_int, ctypes.c_void_p); libc.malloc_info.restype = ctypes.c_int
    libc.fflush.argtypes = (ctypes.c_void_p,); libc.fflush.restype = ctypes.c_int
    libc.ferror.argtypes = (ctypes.c_void_p,); libc.ferror.restype = ctypes.c_int
    libc.ftell.argtypes = (ctypes.c_void_p,); libc.ftell.restype = ctypes.c_long
    libc.fclose.argtypes = (ctypes.c_void_p,); libc.fclose.restype = ctypes.c_int
    libc.free.argtypes = (ctypes.c_void_p,); libc.free.restype = None
    libc.malloc_trim.argtypes = (ctypes.c_size_t,); libc.malloc_trim.restype = ctypes.c_int
    return libc


def heap_info(libc):
    buffer = ctypes.create_string_buffer(HEAP_REPORT_BYTES)
    stream = libc.fmemopen(buffer, len(buffer), b'w')
    if not stream:
        raise RuntimeError('fixed-size fmemopen failed')
    try:
        if libc.malloc_info(0, stream) != 0:
            raise RuntimeError('malloc_info failed')
        if libc.fflush(stream) != 0 or libc.ferror(stream):
            raise RuntimeError('malloc_info exceeded fixed report buffer')
        size = libc.ftell(stream)
        status = libc.fclose(stream); stream = None
        if status != 0 or not 0 < size < len(buffer):
            raise RuntimeError('invalid fixed malloc_info stream')
        return parse_heap(buffer.raw[:size])
    finally:
        if stream:
            libc.fclose(stream)


def providers():
    plan = importlib.import_module('b12x._lib.compile_plan')
    gc_module = importlib.import_module('vllm.utils.gc_utils')
    workspace = importlib.import_module('vllm.v1.worker.workspace')
    graph_module = importlib.import_module('vllm.v1.worker.gpu.cudagraph_utils')
    modules = (plan, gc_module, workspace, graph_module)
    hashes = tuple(hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest() for m in modules)
    if hashes != (PLAN_SHA, GC_SHA, WORKSPACE_SHA, GRAPH_SHA):
        raise RuntimeError('postcapture provider differs from pinned image')
    if plan._RETAINED_PROGRAMS.get() is not None:
        raise RuntimeError('cannot trim during program materialization')
    return plan, workspace, dict(plan_sha256=hashes[0], gc_sha256=hashes[1], workspace_sha256=hashes[2], graph_sha256=hashes[3])


def retention(plan):
    identities = set()
    for retained in tuple(plan._LIVE_RETAINED_PROGRAMS):
        for owner in retained.owners.values():
            for program in plan.program_keys(owner):
                identities.add((program.dialect, program.key, id(owner)))
                if len(identities) > 4096:
                    raise RuntimeError('retained-program observation exceeded bound')
    return dict(retained_program_owners=len(identities), retained_identity_sha256=
                hashlib.sha256(json.dumps(sorted(identities), separators=(',', ':')).encode()).hexdigest())


def snapshot(torch, runner, device, result, phase, libc, plan, workspace, source):
    helper = Path(__file__)
    heap = heap_info(libc)
    pinned = torch.cuda.memory.host_memory_stats()
    return dict(version=1, phase=phase, boundary='post-capture-before-second-warmup',
                pid=os.getpid(), utc_ns=time.time_ns(), device_index=device, result=result,
                kv_bytes=runner.cache_config.kv_cache_memory_bytes,
                graphs_captured=runner.cudagraph_manager._graphs_captured,
                fraction=torch.cuda.memory.get_per_process_memory_fraction(device),
                allocated=torch.cuda.memory_allocated(device), reserved=torch.cuda.memory_reserved(device),
                pinned_owned=pinned['allocated_bytes.current'], pinned_active=pinned['active_bytes.current'],
                gc_enabled=gc.isenabled(), frozen_objects=gc.get_freeze_count(),
                workspace_locked=workspace.current_workspace_manager().is_locked(), heap=heap,
                process=fields('/proc/self/status', ('VmRSS', 'RssAnon')),
                pss=fields('/proc/self/smaps_rollup', ('Rss', 'Pss', 'Pss_Anon', 'Anonymous', 'Private_Dirty',
                           'Shared_Dirty', 'AnonHugePages', 'KSM', 'Swap', 'SwapPss')),
                host=fields('/proc/meminfo', ('MemFree', 'MemAvailable')),
                runner_sha256=hashlib.sha256(helper.with_name('model_runner.py').read_bytes()).hexdigest(),
                helper_sha256=hashlib.sha256(helper.read_bytes()).hexdigest(), **source, **retention(plan))


def emit(row):
    data = (MARKER + json.dumps(row, separators=(',', ':')) + '\n').encode()
    if len(data) > 4096 or os.write(2, data) != len(data):
        raise RuntimeError('invalid postcapture receipt write')


def terminal_hold():
    while True:
        time.sleep(60)


def _after_capture(function, *, observe):
    @wraps(function)
    def wrapped(runner, *args, **kwargs):
        if kwargs.get('profile_only', False):
            return function(runner, *args, **kwargs)
        if runner.cache_config.kv_cache_memory_bytes != 17*1024**3:
            raise RuntimeError('postcapture trim requires explicit17G KV')
        if getattr(runner, '_b12x_postcapture_heap_seen', False):
            raise RuntimeError('postcapture heap return is startup-once')
        if (runner.cudagraph_manager is None or not runner.cudagraph_manager.needs_capture()
                or runner.cudagraph_manager._graphs_captured is not False):
            raise RuntimeError('postcapture trim requires actual graph capture')
        runner._b12x_postcapture_heap_seen = True
        result = function(runner, *args, **kwargs)
        import torch
        from vllm.platforms import current_platform
        if type(result) is not int or runner.cudagraph_manager._graphs_captured is not True:
            raise RuntimeError('capture did not complete with its original metric')
        if runner.device.type != 'cuda' or not torch.cuda.is_initialized():
            raise RuntimeError('postcapture trim requires initialized CUDA')
        device = runner.device.index
        if device is None: device = torch.cuda.current_device()
        if (not current_platform.is_integrated_gpu(device) or torch.cuda.memory.get_allocator_backend() != 'native'
                or torch.cuda.is_current_stream_capturing() or torch.cuda.memory.get_per_process_memory_fraction(device) != 1.0):
            raise RuntimeError('postcapture trim requires integrated/native restored CUDA outside capture')
        plan, workspace, source = providers(); libc = libc_api()
        if observe:
            row = snapshot(torch, runner, device, result, 'observe', libc, plan, workspace, source)
            emit(row)
            # Terminal diagnosis: never continue into second warmup/serving.
            terminal_hold()
            raise RuntimeError('terminal postcapture observer unexpectedly returned')
        before = snapshot(torch, runner, device, result, 'before', libc, plan, workspace, source)
        emit(before)
        if before['host']['MemAvailable'] < FLOOR or not before['workspace_locked'] or not before['retained_program_owners']:
            raise RuntimeError('unsafe/unowned postcapture boundary; refuse second warmup')
        if before['heap']['free_chunk_bytes'] < MINIMUM_RETURN:
            raise RuntimeError('insufficient observed free glibc chunks; refuse second warmup')
        started = time.monotonic_ns(); returned = libc.malloc_trim(0)
        after = snapshot(torch, runner, device, result, 'after', libc, plan, workspace, source)
        after.update(trim_result=returned, elapsed_ns=time.monotonic_ns()-started)
        emit(after)
        for key in ('result', 'kv_bytes', 'fraction', 'allocated', 'reserved', 'pinned_owned', 'pinned_active',
                    'workspace_locked', 'gc_enabled', 'frozen_objects', 'retained_program_owners', 'retained_identity_sha256'):
            if before[key] != after[key]:
                raise RuntimeError('postcapture trim changed live state: '+key)
        if (after['host']['MemAvailable'] < FLOOR or returned != 1
                or before['process']['RssAnon']-after['process']['RssAnon'] < MINIMUM_RETURN
                or after['host']['MemAvailable']-before['host']['MemAvailable'] < MINIMUM_AVAILABLE_GAIN):
            raise RuntimeError('postcapture heap return failed256MiB/128MiB gate; refuse second warmup')
        return result
    return wrapped


def return_heap_after_capture(function):
    return _after_capture(function, observe=False)


def observe_after_capture(function):
    return _after_capture(function, observe=True)
