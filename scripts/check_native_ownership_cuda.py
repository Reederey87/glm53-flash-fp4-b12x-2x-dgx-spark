"""Model-free common pinned return + terminal collector preserves real graphs."""
import argparse
import importlib
import json
import os
from pathlib import Path
import sys
import types
from unittest.mock import patch
import torch
from b12x._lib import compiler
from b12x.gemm import bf16_gemv
from b12x.preparation import PreparationSession, PreparedCall
import vllm.model_executor.warmup.b12x_prepare
from vllm.v1.worker.workspace import init_workspace_manager, current_workspace_manager, reset_workspace_manager


class Terminal(BaseException):
    pass


@torch.inference_mode()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--device-spelling',choices=('indexed','unindexed'),required=True)
    args=parser.parse_args()
    native=importlib.import_module('vllm.v1.worker._b12x_native_ownership')
    pinned_helper=importlib.import_module('vllm.v1.worker._b12x_startup_pinned')
    torch.cuda.init();index=torch.cuda.current_device();torch.manual_seed(17)
    device=torch.device(f'cuda:{index}' if args.device_spelling=='indexed' else 'cuda')
    init_workspace_manager(device)
    upload,=current_workspace_manager().get_simultaneous(((1024**2,),torch.uint8))
    source=torch.randn(2,2048,device=device,dtype=torch.bfloat16)
    weight=torch.randn(96,2048,device=device,dtype=torch.bfloat16)
    pinned=torch.ones(1024**2,dtype=torch.uint8,pin_memory=True)
    plan=bf16_gemv.plan(bf16_gemv.query_from_call(source,weight))
    request=plan.request(name='native-ownership-probe',prepare_call=lambda state:PreparedCall(run=lambda:state.run(source,weight)))
    graph=torch.cuda.CUDAGraph();host_graph=torch.cuda.CUDAGraph();packets=[]
    with PreparationSession(device=device,autotune=False,compile_workers=1) as session:
        session.prepare((request,))
        with session.capture(),torch.cuda.graph(graph):
            output=bf16_gemv.mm(source,weight,plan=plan)
        with torch.cuda.graph(host_graph):upload.copy_(pinned,non_blocking=True)
        torch.cuda.synchronize()
        pointers=(source.data_ptr(),weight.data_ptr(),output.data_ptr(),pinned.data_ptr(),upload.data_ptr())
        idle=[torch.ones(512*1024**2,dtype=torch.uint8,pin_memory=True)]
        worker=types.SimpleNamespace(device=device,cache_config=types.SimpleNamespace(kv_cache_memory_bytes=17*1024**3),
            _b12x_startup_coordinator=None,_b12x_stage=None,_b12x_profile_batch=None,_b12x_tuning_cache=False)
        @native.observe_native_owners_terminal
        @pinned_helper.release_after_explicit_profile
        def explicit_profile_stub(owner):
            idle.clear();torch.cuda.synchronize()
            return 17*1024**3
        emit=native.emit
        def capture_emit(marker,row):
            packets.append((marker,row));emit(marker,row)
        def forbidden(*a,**kw):raise AssertionError('compiler/loader invoked during observation or replay')
        try:
            with patch.object(compiler,'compile',forbidden),patch.object(compiler,'_load_cute_compile_from_disk',forbidden),patch.object(native,'terminal_hold',side_effect=Terminal),patch.object(native,'emit',side_effect=capture_emit):
                try:explicit_profile_stub(worker)
                except Terminal:pass
                else:raise AssertionError('terminal observer returned')
            assert not idle
            assert packets[-1][0]==native.MARKER
            assert packets[-1][1]['inventory_complete'] is True
            assert pointers==(source.data_ptr(),weight.data_ptr(),output.data_ptr(),pinned.data_ptr(),upload.data_ptr())
            with patch.object(compiler,'compile',forbidden),patch.object(compiler,'_load_cute_compile_from_disk',forbidden):
                for number in (3,7,11):
                    pinned.fill_(number);upload.zero_();host_graph.replay()
                    source.copy_(torch.randn_like(source));output.fill_(float('nan'));graph.replay();torch.cuda.synchronize()
                    assert torch.equal(upload,torch.full_like(upload,number))
                    assert torch.equal(pinned,torch.full_like(pinned,number))
                    torch.testing.assert_close(output,(source.float()@weight.float().T).bfloat16(),rtol=2e-2,atol=2e-2)
            assert pointers==(source.data_ptr(),weight.data_ptr(),output.data_ptr(),pinned.data_ptr(),upload.data_ptr())
            print(json.dumps(dict(device=str(device),pid=os.getpid(),terminal_collector=True,
                common_pinned_return_completed=True,prepared_b12x_replays=3,pinned_copy_replays=3,
                pointers_preserved=True,compiler_and_loader_forbidden=True,checkpoint_loaded=False,
                admission_stub_not_model_profile=True,server_loaded=False)),flush=True)
        finally:
            graph.reset();host_graph.reset()
    reset_workspace_manager()


if __name__=='__main__':main()
