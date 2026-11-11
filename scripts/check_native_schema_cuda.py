"""NONQUALIFYING native schema exploration; no common pinned-return treatment."""
import importlib
import json
import types
from unittest.mock import patch
import torch
from b12x._lib import compiler
from b12x.gemm import bf16_gemv
from b12x.preparation import PreparationSession, PreparedCall
import vllm.model_executor.warmup.b12x_prepare
from native_ownership_receipt import validate_graph


@torch.inference_mode()
def main():
    metadata=importlib.import_module('vllm.v1.worker._b12x_native_metadata')
    torch.cuda.init();torch.manual_seed(17)
    device=torch.device('cuda')
    source=torch.randn(2,2048,device=device,dtype=torch.bfloat16)
    weight=torch.randn(96,2048,device=device,dtype=torch.bfloat16)
    pinned=torch.ones(1024**2,dtype=torch.uint8,pin_memory=True)
    upload=torch.empty_like(pinned,device=device)
    plan=bf16_gemv.plan(bf16_gemv.query_from_call(source,weight))
    request=plan.request(name='native-schema-probe',prepare_call=lambda state:PreparedCall(run=lambda:state.run(source,weight)))
    graph=torch.cuda.CUDAGraph();host_graph=torch.cuda.CUDAGraph()
    with PreparationSession(device=device,autotune=False,compile_workers=1) as session:
        session.prepare((request,))
        try:
            with session.capture(),torch.cuda.graph(graph):output=bf16_gemv.mm(source,weight,plan=plan)
            with torch.cuda.graph(host_graph):upload.copy_(pinned,non_blocking=True)
            torch.cuda.synchronize()
            pointers=(source.data_ptr(),weight.data_ptr(),output.data_ptr(),pinned.data_ptr(),upload.data_ptr())
            plan_module,classes=metadata.providers()
            def forbidden(*args,**kwargs):raise AssertionError('collector/replay called compiler or loader')
            with patch.object(compiler,'compile',forbidden),patch.object(compiler,'_load_cute_compile_from_disk',forbidden):
                report=metadata.collect(plan_module,classes)
                print('B12X_NATIVE_SCHEMA '+json.dumps(report,separators=(',',':')),flush=True)
                assert report['complete'] is True
                validate_graph(report)
                for number in (3,7,11):
                    pinned.fill_(number);upload.zero_();host_graph.replay()
                    source.copy_(torch.randn_like(source));output.fill_(float('nan'));graph.replay();torch.cuda.synchronize()
                    assert torch.equal(upload,torch.full_like(upload,number))
                    torch.testing.assert_close(output,(source.float()@weight.float().T).bfloat16(),rtol=2e-2,atol=2e-2)
            assert pointers==(source.data_ptr(),weight.data_ptr(),output.data_ptr(),pinned.data_ptr(),upload.data_ptr())
            print(json.dumps(dict(schema_exploration=True,common_pinned_qualified=False,checkpoint_deployment_cleared=False,
                checkpoint_loaded=False,server_loaded=False,compiler_loader_forbidden_during_collection_and_replay=True,
                prepared_b12x_graph_replays=3,pinned_copy_replays=3,pointers_preserved=True)),flush=True)
        finally:
            graph.reset();host_graph.reset()


if __name__=='__main__':main()
