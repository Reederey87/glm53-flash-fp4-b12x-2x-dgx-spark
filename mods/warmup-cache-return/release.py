"""Return only unoccupied CUDA cache after the original warmup frame exits."""
from functools import wraps
import hashlib
import json
import os
from pathlib import Path
import time


def return_unused_cuda_cache(function):
    @wraps(function)
    def wrapped(worker,*args,**kwargs):
        result=function(worker,*args,**kwargs)
        import torch
        from vllm.platforms import current_platform
        if worker.device.type!='cuda' or not torch.cuda.is_initialized():
            raise RuntimeError('warmup cache return requires initialized CUDA')
        device=worker.device.index
        if device is None:device=torch.cuda.current_device()
        if not current_platform.is_integrated_gpu(device):
            raise RuntimeError('warmup cache return requires integrated CUDA')
        if torch.cuda.memory.get_allocator_backend()!='native':
            raise RuntimeError('warmup cache return requires native allocator')
        if torch.cuda.is_current_stream_capturing():
            raise RuntimeError('cannot return cache during graph capture')
        if torch.cuda.memory.get_per_process_memory_fraction(device)!=1.0:
            raise RuntimeError('postload allocator bound was not restored')
        helper=Path(__file__)
        hashes=dict(worker_sha256=hashlib.sha256(helper.with_name('gpu_worker.py').read_bytes()).hexdigest(),
                    helper_sha256=hashlib.sha256(helper.read_bytes()).hexdigest())
        records=[]
        for phase in ('before','after'):
            if phase=='after':torch.cuda.empty_cache()
            host={}
            with open('/proc/meminfo') as source:
                for line in source:
                    name,value=line.split(':',1)
                    if name in ('MemAvailable','MemFree'):host[name]=int(value.split()[0])*1024
            record=dict(phase=phase,pid=os.getpid(),utc_ns=time.time_ns(),device_index=device,
                allocated=torch.cuda.memory_allocated(device),reserved=torch.cuda.memory_reserved(device),
                fraction=torch.cuda.memory.get_per_process_memory_fraction(device),host=host,**hashes)
            data=('B12X_WARMUP_CACHE '+json.dumps(record,separators=(',',':'))+'\n').encode()
            if len(data)>4096:raise RuntimeError('warmup cache receipt too large')
            os.write(2,data);records.append(record)
        if records[1]['allocated']!=records[0]['allocated'] or records[1]['reserved']>records[0]['reserved']:
            raise RuntimeError('cache return changed live allocation accounting')
        return result
    return wrapped
