"""Bounded real glibc/CUDA compatibility fixture; no model checkpoint/server."""
import ctypes
import importlib.util
import json
from pathlib import Path
import types
import torch

path=Path('/usr/local/lib/python3.12/dist-packages/vllm/v1/worker/_b12x_explicit_kv_host_trim.py')
spec=importlib.util.spec_from_file_location('trim_probe',path)
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
torch.cuda.init(); index=torch.cuda.current_device()
libc=ctypes.CDLL(None)
libc.malloc.argtypes=(ctypes.c_size_t,); libc.malloc.restype=ctypes.c_void_p
libc.free.argtypes=(ctypes.c_void_p,); libc.free.restype=None
results=[]
for spelling in ('cuda',f'cuda:{index}'):
    worker=types.SimpleNamespace(device=torch.device(spelling),cache_config=types.SimpleNamespace(kv_cache_memory_bytes=17*1024**3))
    value=torch.ones(16,device=worker.device)
    stream=torch.cuda.Stream(); stream.wait_stream(torch.cuda.current_stream())
    with torch.cuda.stream(stream):
        for _ in range(3): output=value+1
    torch.cuda.current_stream().wait_stream(stream)
    graph=torch.cuda.CUDAGraph()
    with torch.cuda.graph(graph): output=value+1
    pinned=torch.ones(1024*1024,dtype=torch.uint8,pin_memory=True)
    pointers=(value.data_ptr(),output.data_ptr(),pinned.data_ptr())
    blocks=[]; guards=[]
    try:
        #64KiB chunks are below glibc's mmap threshold. Live guards prevent
        #automatic top-chunk release, leaving >1GiB free interior pages.
        for number in range(20480):
            pointer=libc.malloc(65536)
            if not pointer: raise MemoryError('bounded CPU probe allocation failed')
            blocks.append(pointer); ctypes.memset(pointer,37,65536)
        for number,pointer in enumerate(blocks):
            if number%64==0 or number==len(blocks)-1: guards.append(pointer)
            else:
                libc.free(pointer)
                blocks[number]=None
        @module.trim_after_explicit_profile
        def profile(owner): return 17*1024**3-2048
        assert profile(worker)==17*1024**3-2048
        assert all(ctypes.string_at(pointer,16)==b'%'*16 for pointer in guards)
        assert torch.equal(pinned,torch.ones_like(pinned))
        for number in (3.,7.,11.):
            value.fill_(number); graph.replay()
            assert torch.equal(output,torch.full_like(output,number+1))
        assert pointers==(value.data_ptr(),output.data_ptr(),pinned.data_ptr())
        results.append(dict(device=spelling,same_one_GiB_gate_passed=True,live_CPU_guards_preserved=True,live_pinned_preserved=True,graph_replays=3,pointers_preserved=True))
    finally:
        for pointer in blocks:
            if pointer is not None: libc.free(pointer)
    del graph,value,output,pinned
print(json.dumps(dict(pytorch=torch.__version__,checks=results,checkpoint_loaded=False,server_loaded=False,cpu_fixture_bytes=20480*65536)))
