"""Real prepared B12X graph survives lookup eviction under the full return gate."""
import ctypes
import importlib.util
import json
from pathlib import Path
import types
from unittest.mock import patch
import weakref
import torch
from b12x._lib import compiler
from b12x.gemm import bf16_gemv
from b12x.preparation import PreparationSession,PreparedCall

path=Path('/usr/local/lib/python3.12/dist-packages/vllm/v1/worker/_b12x_compiler_release.py')
spec=importlib.util.spec_from_file_location('release_probe',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
torch.cuda.init();index=torch.cuda.current_device();torch.manual_seed(17)
libc=ctypes.CDLL(None);libc.malloc.argtypes=(ctypes.c_size_t,);libc.malloc.restype=ctypes.c_void_p
libc.free.argtypes=(ctypes.c_void_p,);libc.free.restype=None
results=[]
for spelling in ('cuda',f'cuda:{index}'):
    worker=types.SimpleNamespace(device=torch.device(spelling),cache_config=types.SimpleNamespace(kv_cache_memory_bytes=17*1024**3))
    source=torch.randn(2,2048,device=worker.device,dtype=torch.bfloat16)
    weight=torch.randn(96,2048,device=worker.device,dtype=torch.bfloat16)
    pinned=torch.ones(1024*1024,dtype=torch.uint8,pin_memory=True)
    plan=bf16_gemv.plan(bf16_gemv.query_from_call(source,weight))
    request=plan.request(name='release-probe',prepare_call=lambda state:PreparedCall(run=lambda:state.run(source,weight)))
    blocks=[];guards=[];retired=[]
    class CacheOwner:
        def __del__(self):
            for number in retired:
                pointer=blocks[number]
                if pointer is not None:libc.free(pointer);blocks[number]=None
    with PreparationSession(device=worker.device,autotune=False,compile_workers=1) as session:
        session.prepare((request,));graph=torch.cuda.CUDAGraph()
        try:
            with session.capture(),torch.cuda.graph(graph):output=bf16_gemv.mm(source,weight,plan=plan)
            pointers=(source.data_ptr(),weight.data_ptr(),output.data_ptr(),pinned.data_ptr())
            torch.cuda.synchronize()
            for number in range(20480):
                pointer=libc.malloc(65536)
                if not pointer:raise MemoryError('bounded CPU fixture allocation failed')
                blocks.append(pointer);ctypes.memset(pointer,37,65536)
                (guards if number%64==0 or number==20479 else retired).append(number)
            owner=CacheOwner();reference=weakref.ref(owner)
            with compiler._MEMORY_CACHE_LOCK:compiler._MEMORY_CACHE[('release-fixture',spelling)]=owner
            with compiler._SPEC_MEMO_LOCK:compiler._SPEC_MEMO[('release-fixture',spelling)]=owner
            del owner
            @module.release_after_explicit_profile
            def profile(owner):return 17*1024**3
            assert profile(worker)==17*1024**3
            assert reference() is None
            assert all(ctypes.string_at(blocks[number],16)==b'%'*16 for number in guards)
            assert torch.equal(pinned,torch.ones_like(pinned))
            def forbidden(*args,**kwargs):raise AssertionError('prepared replay called compiler or loader')
            with patch.object(compiler,'compile',forbidden),patch.object(compiler,'_load_cute_compile_from_disk',forbidden):
                for _ in range(3):
                    source.copy_(torch.randn_like(source));output.fill_(float('nan'));graph.replay();torch.cuda.synchronize()
                    torch.testing.assert_close(output,(source.float()@weight.float().T).bfloat16(),rtol=2e-2,atol=2e-2)
            assert pointers==(source.data_ptr(),weight.data_ptr(),output.data_ptr(),pinned.data_ptr())
            results.append(dict(device=spelling,b12x_graph_replays=3,pointers_preserved=True,compiler_and_loader_forbidden=True,cache_owned_fixture_released=True,same_one_GiB_gate_passed=True))
        finally:
            compiler.clear_compile_cache();graph.reset()
            for number,pointer in enumerate(blocks):
                if pointer is not None:libc.free(pointer);blocks[number]=None
    del source,weight,output,pinned
print(json.dumps(dict(pytorch=torch.__version__,checks=results,checkpoint_loaded=False,server_loaded=False,cpu_fixture_bytes=20480*65536)))
