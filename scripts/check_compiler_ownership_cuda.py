"""Real diagnostic API check with controlled metadata, no checkpoint/server."""
import importlib.util
import json
from pathlib import Path
import time
import types
import torch
from torch._inductor.output_code import CompiledFxGraph
from vllm.v1.worker._b12x_compiler_metadata import compiler_summary

path=Path('/usr/local/lib/python3.12/dist-packages/vllm/v1/worker/_b12x_compiler_ownership.py')
spec=importlib.util.spec_from_file_location('compiler_probe',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
torch.cuda.init();index=torch.cuda.current_device();results=[]
blob=b'PRIVATE-COMPILER-PAYLOAD'*65536
first=object.__new__(CompiledFxGraph);second=object.__new__(CompiledFxGraph)
first.compiled_fn_runner=None;second.compiled_fn_runner=None
first.source_code=blob;second.source_code=blob
summary=compiler_summary([first,second])
assert summary['unique_payload_objects']==1 and summary['unique_payload_bytes']>=len(blob)
assert 'PRIVATE-COMPILER-PAYLOAD' not in json.dumps(summary)


def hold(seconds):
    assert seconds==120
    raise StopIteration('intentional probe boundary')


module.time=types.SimpleNamespace(time_ns=time.time_ns,sleep=hold)
for spelling in ('cuda',f'cuda:{index}'):
    worker=types.SimpleNamespace(device=torch.device(spelling),cache_config=types.SimpleNamespace(kv_cache_memory_bytes=17*1024**3))
    value=torch.ones(16,device=worker.device);pinned=torch.ones(1024*1024,dtype=torch.uint8,pin_memory=True)
    stream=torch.cuda.Stream();stream.wait_stream(torch.cuda.current_stream())
    with torch.cuda.stream(stream):
        for _ in range(3):output=value+1
    torch.cuda.current_stream().wait_stream(stream)
    graph=torch.cuda.CUDAGraph()
    with torch.cuda.graph(graph):output=value+1
    pointers=(value.data_ptr(),output.data_ptr(),pinned.data_ptr())
    @module.observe_compiler_ownership
    def profile(owner):return 17*1024**3
    try:profile(worker)
    except StopIteration as error:assert str(error)=='intentional probe boundary'
    else:raise AssertionError('diagnostic returned to KV allocation')
    assert first.source_code is blob and second.source_code is blob
    value.fill_(7);graph.replay();assert torch.equal(output,torch.full_like(output,8))
    assert torch.equal(pinned,torch.ones_like(pinned))
    assert pointers==(value.data_ptr(),output.data_ptr(),pinned.data_ptr())
    results.append(dict(device=spelling,terminal_hold_reached=True,metadata_preserved=True,payload_deduplicated=True,graph_and_pinned_preserved=True))
    del graph,value,output,pinned
print(json.dumps(dict(pytorch=torch.__version__,checks=results,checkpoint_loaded=False,server_loaded=False)))
