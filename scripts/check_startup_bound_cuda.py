"""Tiny compatibility test INSIDE an ephemeral pinned CUDA container only.

Run both startup mods first. No checkpoint, server, quantization or KV is loaded.
"""
import importlib.util
import json
import math
from pathlib import Path
import torch

helper=Path('/usr/local/lib/python3.12/dist-packages/vllm/model_executor/model_loader/_b12x_startup_bound.py')
spec=importlib.util.spec_from_file_location('startup_bound_probe',helper)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
torch.cuda.init()
index=torch.cuda.current_device()
assert torch.cuda.memory.get_allocator_backend()=='native'
assert torch.cuda.memory.get_per_process_memory_fraction(index)==1.0
results=[]
for spelling in ('cuda',f'cuda:{index}'):
    for fail in (False,True):
        device=torch.device(spelling)
        @module.bounded_postload
        def body(model,config,target):
            assert target is device
            assert math.isclose(torch.cuda.memory.get_per_process_memory_fraction(index),.8,rel_tol=0,abs_tol=1e-9)
            tensor=torch.empty(1024*1024,dtype=torch.uint8,device=target)
            del tensor
            if fail:raise RuntimeError('expected probe failure')
            return model
        try:
            assert body('sentinel',None,device)=='sentinel'
            assert not fail
        except RuntimeError as error:
            assert fail and str(error)=='expected probe failure'
        assert torch.cuda.memory.get_per_process_memory_fraction(index)==1.0
        results.append(dict(device=spelling,exception=fail,restored=True))
print(json.dumps(dict(pytorch=torch.__version__,device_index=index,checks=results,server_loaded=False,checkpoint_loaded=False)))
