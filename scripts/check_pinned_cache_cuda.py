"""Real pinned-staging return preserves live host-copy and prepared B12X graphs."""
import importlib.util
import json
from pathlib import Path
import types
from unittest.mock import patch
import torch
from b12x._lib import compiler
from b12x.gemm import bf16_gemv
from b12x.preparation import PreparationSession, PreparedCall


def main():
    path = Path('/usr/local/lib/python3.12/dist-packages/vllm/v1/worker/_b12x_startup_pinned.py')
    spec = importlib.util.spec_from_file_location('pinned_probe', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    torch.cuda.init(); index = torch.cuda.current_device(); torch.manual_seed(17)
    results = []
    for spelling in ('cuda', f'cuda:{index}'):
        worker = types.SimpleNamespace(device=torch.device(spelling), cache_config=types.SimpleNamespace(kv_cache_memory_bytes=17*1024**3))
        source = torch.randn(2, 2048, device=worker.device, dtype=torch.bfloat16)
        weight = torch.randn(96, 2048, device=worker.device, dtype=torch.bfloat16)
        pinned = torch.ones(1024**2, dtype=torch.uint8, pin_memory=True)
        upload = torch.empty_like(pinned, device=worker.device)
        host_graph = torch.cuda.CUDAGraph()
        with torch.cuda.graph(host_graph):
            upload.copy_(pinned, non_blocking=True)
        plan = bf16_gemv.plan(bf16_gemv.query_from_call(source, weight))
        request = plan.request(name='pinned-probe', prepare_call=lambda state: PreparedCall(run=lambda: state.run(source, weight)))
        with PreparationSession(device=worker.device, autotune=False, compile_workers=1) as session:
            session.prepare((request,)); graph = torch.cuda.CUDAGraph()
            try:
                with session.capture(), torch.cuda.graph(graph):
                    output = bf16_gemv.mm(source, weight, plan=plan)
                pointers = (source.data_ptr(), weight.data_ptr(), output.data_ptr(), pinned.data_ptr(), upload.data_ptr())
                staging = torch.empty(512*1024**2, dtype=torch.uint8, pin_memory=True)
                staging.fill_(37); del staging
                @module.release_after_explicit_profile
                def profile(owner):
                    torch.cuda.synchronize()
                    return 17*1024**3
                assert profile(worker) == 17*1024**3
                def forbidden(*args, **kwargs):
                    raise AssertionError('prepared replay called compiler or loader')
                with patch.object(compiler, 'compile', forbidden), patch.object(compiler, '_load_cute_compile_from_disk', forbidden):
                    for number in (3, 7, 11):
                        pinned.fill_(number); upload.zero_(); host_graph.replay()
                        source.copy_(torch.randn_like(source)); output.fill_(float('nan')); graph.replay(); torch.cuda.synchronize()
                        assert torch.equal(upload, torch.full_like(upload, number))
                        assert torch.equal(pinned, torch.full_like(pinned, number))
                        torch.testing.assert_close(output, (source.float()@weight.float().T).bfloat16(), rtol=2e-2, atol=2e-2)
                assert pointers == (source.data_ptr(), weight.data_ptr(), output.data_ptr(), pinned.data_ptr(), upload.data_ptr())
                results.append(dict(device=spelling, known_idle_staging_bytes=512*1024**2, full_reclamation_gate=True,
                                    live_pinned_graph_replays=3, prepared_b12x_graph_replays=3,
                                    pointers_preserved=True, compiler_and_loader_forbidden=True))
            finally:
                graph.reset()
        host_graph.reset()
        del graph, host_graph, source, weight, output, pinned, upload, plan, request
    print(json.dumps(dict(pytorch=torch.__version__, checks=results, checkpoint_loaded=False, server_loaded=False)))


if __name__ == '__main__':
    main()
