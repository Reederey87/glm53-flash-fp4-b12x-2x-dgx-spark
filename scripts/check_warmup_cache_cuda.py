"""Real graph-replay compatibility check, only in a disposable pinned container."""
import importlib.util
import json
from pathlib import Path
import types
import torch

path=Path('/usr/local/lib/python3.12/dist-packages/vllm/v1/worker/_b12x_warmup_cache.py')
spec=importlib.util.spec_from_file_location('warmup_cache_probe',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
torch.cuda.init();index=torch.cuda.current_device();results=[]
for spelling in ('cuda',f'cuda:{index}'):
    device=torch.device(spelling);worker=types.SimpleNamespace(device=device)
    value=torch.ones(16,device=device)
    stream=torch.cuda.Stream();stream.wait_stream(torch.cuda.current_stream())
    with torch.cuda.stream(stream):
        for _ in range(3):output=value+1
    torch.cuda.current_stream().wait_stream(stream)
    graph=torch.cuda.CUDAGraph()
    with torch.cuda.graph(graph):output=value+1
    pointers=(value.data_ptr(),output.data_ptr())
    @module.return_unused_cuda_cache
    def warmup(owner):
        temporary=torch.empty(32*1024**2,dtype=torch.uint8,device=owner.device)
        del temporary
        return 'warmup-result'
    assert warmup(worker)=='warmup-result'
    for number in (3.,7.,11.):
        value.fill_(number);graph.replay()
        assert torch.equal(output,torch.full_like(output,number+1))
        assert pointers==(value.data_ptr(),output.data_ptr())
    results.append(dict(device=spelling,replays=3,pointers_preserved=True,output_correct=True))
    del graph,output,value
torch.cuda.empty_cache()
print(json.dumps(dict(pytorch=torch.__version__,checks=results,server_loaded=False,checkpoint_loaded=False)))
