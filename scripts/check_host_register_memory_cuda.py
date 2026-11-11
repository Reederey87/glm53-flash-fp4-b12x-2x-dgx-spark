"""Same-size default/register host-memory comparison; no checkpoint clearance."""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import sys
import types
from unittest.mock import patch
import torch
from b12x._lib import compiler
from b12x.gemm import bf16_gemv
from b12x.preparation import PreparationSession,PreparedCall
import vllm.model_executor.warmup.b12x_prepare
from vllm.v1.worker.workspace import init_workspace_manager,current_workspace_manager,reset_workspace_manager
from check_pinned_residency_cuda import sample


@torch.inference_mode()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=('default','register'),required=True);args=parser.parse_args()
    expected='pinned_use_cuda_host_register:True' if args.mode=='register' else ''
    if (sys.flags.optimize!=0 or os.environ.get('PYTORCH_CUDA_ALLOC_CONF')!=expected
            or os.environ.get('PYTORCH_ALLOC_CONF') or os.environ.get('PYTORCH_HIP_ALLOC_CONF')):
        raise RuntimeError('unexpected process-start configuration/optimized interpreter')
    if torch.version.git_version!='cf30153c4c131c8164ee7798e5022d810682e2cb':raise RuntimeError('wrong Torch revision')
    torch.cuda.init();torch.manual_seed(17);device=torch.device('cuda')
    effective=torch._C._accelerator_getAllocatorSettings()
    if torch.cuda.memory.get_allocator_backend()!='native' or effective!=expected:
        raise RuntimeError('effective allocator differs from frozen treatment')
    helper=importlib.import_module('vllm.v1.worker._b12x_startup_pinned')
    helper_sha=hashlib.sha256(Path(helper.__file__).read_bytes()).hexdigest()
    if helper_sha!='1761e9aeb863da2cb307fc7094c30af495aa78ff9e135e9d58d81df7b6c82ac6':raise RuntimeError('wrong common helper')
    init_workspace_manager(device)
    upload,=current_workspace_manager().get_simultaneous(((1024**2,),torch.uint8))
    source=torch.randn(2,2048,device=device,dtype=torch.bfloat16);weight=torch.randn(96,2048,device=device,dtype=torch.bfloat16)
    pinned=torch.ones(1024**2,dtype=torch.uint8,pin_memory=True)
    plan=bf16_gemv.plan(bf16_gemv.query_from_call(source,weight))
    request=plan.request(name='host-register-memory-probe',prepare_call=lambda state:PreparedCall(run=lambda:state.run(source,weight)))
    graph=torch.cuda.CUDAGraph();host_graph=torch.cuda.CUDAGraph();rows=[]
    with PreparationSession(device=device,autotune=False,compile_workers=1) as session:
        session.prepare((request,))
        try:
            with session.capture(),torch.cuda.graph(graph):output=bf16_gemv.mm(source,weight,plan=plan)
            with torch.cuda.graph(host_graph):upload.copy_(pinned,non_blocking=True)
            torch.cuda.synchronize();rows.append(sample('before-fixture'))
            if torch._C._accelerator_getAllocatorSettings()!=expected:
                raise RuntimeError('allocator treatment changed during preparation/capture')
            if rows[-1]['host']['MemAvailable']<10*1024**3:raise RuntimeError('micro requires10GiB headroom')
            pointers=(source.data_ptr(),weight.data_ptr(),output.data_ptr(),pinned.data_ptr(),upload.data_ptr())
            idle=[torch.ones(512*1024**2,dtype=torch.uint8,pin_memory=True)]
            rows.append(sample('resident-fixture'))
            worker=types.SimpleNamespace(device=device,cache_config=types.SimpleNamespace(kv_cache_memory_bytes=17*1024**3),
                _b12x_startup_coordinator=None,_b12x_profile_batch=None)
            @helper.release_after_explicit_profile
            def profile_stub(owner):
                idle.clear();rows.append(sample('cached-before-helper'))
                torch.cuda.synchronize();return 17*1024**3
            failure=None
            try:profile_stub(worker)
            except RuntimeError as error:failure=str(error)
            rows.append(sample('after-helper-or-exception'))
            live_unchanged=(rows[-2]['allocated']==rows[-1]['allocated'] and rows[-2]['reserved']==rows[-1]['reserved']
                and rows[-2]['pinned']['active_bytes.current']==rows[-1]['pinned']['active_bytes.current'])
            qualified=failure is None and live_unchanged
            def forbidden(*a,**kw):raise AssertionError('prepared replay called compiler or loader')
            with patch.object(compiler,'compile',forbidden),patch.object(compiler,'_load_cute_compile_from_disk',forbidden):
                for number in (3,7,11):
                    pinned.fill_(number);upload.zero_();host_graph.replay()
                    source.copy_(torch.randn_like(source));output.fill_(float('nan'));graph.replay();torch.cuda.synchronize()
                    if not torch.equal(upload,torch.full_like(upload,number)):raise RuntimeError('host graph replay mismatch')
                    torch.testing.assert_close(output,(source.float()@weight.float().T).bfloat16(),rtol=2e-2,atol=2e-2)
            if pointers!=(source.data_ptr(),weight.data_ptr(),output.data_ptr(),pinned.data_ptr(),upload.data_ptr()):
                raise RuntimeError('live storage pointers changed')
            if torch._C._accelerator_getAllocatorSettings()!=expected:
                raise RuntimeError('allocator treatment changed during observation/replay')
            print('B12X_HOST_REGISTER_MEMORY '+json.dumps(dict(mode=args.mode,effective_allocator_settings=effective,
                helper_sha256=helper_sha,rows=rows,fixture_bytes=512*1024**2,
                helper_gate_passed=failure is None,helper_failure=failure,micro_physical_and_graph_qualified=qualified,
                live_state_unchanged=live_unchanged,effective_settings_preserved=True,
                prepared_b12x_graph_replays=3,pinned_copy_replays=3,pointers_preserved=True,compiler_loader_forbidden_during_replay=True,
                admission_stub_not_model_profile=True,checkpoint_loaded=False,server_loaded=False,
                os_page_locking_proven=False,checkpoint_deployment_cleared=False),separators=(',',':')),flush=True)
        finally:graph.reset();host_graph.reset()
    reset_workspace_manager()


if __name__=='__main__':main()
