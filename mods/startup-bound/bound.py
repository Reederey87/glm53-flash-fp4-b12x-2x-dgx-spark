"""Bound native allocator cache growth only while postprocessing weights."""
from functools import wraps
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import time

FRACTION = 0.80
SCOPES = itertools.count(1)


def bounded_postload(function):
    @wraps(function)
    def wrapped(model, model_config, target_device):
        import torch
        from vllm.platforms import current_platform

        if target_device.type != 'cuda' or not torch.cuda.is_initialized():
            raise RuntimeError('startup bound requires an initialized CUDA worker')
        # Fraction APIs do not accept an unindexed torch.device('cuda'). The
        # loader passes that spelling, while statistics APIs accept it.
        device = target_device.index
        if device is None:
            device = torch.cuda.current_device()
        if not current_platform.is_integrated_gpu(device):
            raise RuntimeError('startup bound requires an integrated GPU')
        memory = torch.cuda.memory
        backend = memory.get_allocator_backend()
        if backend != 'native':
            raise RuntimeError('startup bound requires the native allocator')
        previous = memory.get_per_process_memory_fraction(device)
        if not math.isclose(previous, 1.0, rel_tol=0, abs_tol=1e-9):
            raise RuntimeError('startup bound prior fraction differs from frozen default')
        total = torch.cuda.get_device_properties(device).total_memory
        # Match this pinned allocator's std::round when converting to bytes.
        limit = int(math.floor(total * FRACTION + .5))
        if memory.memory_reserved(device) > limit:
            raise RuntimeError('startup bound entry reservation already exceeds limit')
        scope = next(SCOPES)
        helper_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        loader_hash = hashlib.sha256(Path(__file__).with_name('utils.py').read_bytes()).hexdigest()

        def event(kind, success):
            record = dict(event=kind, scope=scope, pid=os.getpid(), utc_ns=time.time_ns(),backend=backend,device_index=device,
                fraction=memory.get_per_process_memory_fraction(device), previous=previous,
                requested=FRACTION, capacity=total, limit=limit, success=success,
                allocated=memory.memory_allocated(device), reserved=memory.memory_reserved(device),
                loader_sha256=loader_hash, bound_sha256=helper_hash)
            data=('B12X_STARTUP_BOUND '+json.dumps(record,separators=(',',':'))+'\n').encode()
            if len(data)>4096: raise RuntimeError('startup-bound record exceeded atomic-write bound')
            os.write(2,data)

        success=False
        try:
            memory.set_per_process_memory_fraction(FRACTION,device)
            if not math.isclose(memory.get_per_process_memory_fraction(device),FRACTION,rel_tol=0,abs_tol=1e-9):
                raise RuntimeError('startup allocator fraction did not take effect')
            event('enter',False)
            result=function(model,model_config,target_device)
            success=True
            return result
        finally:
            memory.set_per_process_memory_fraction(previous,device)
            if not math.isclose(memory.get_per_process_memory_fraction(device),previous,rel_tol=0,abs_tol=1e-9):
                raise RuntimeError('startup allocator fraction was not restored')
            event('exit',success)
    return wrapped
