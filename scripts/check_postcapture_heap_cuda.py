"""Exercise the installed V2 capture/GC/lock path with real graphs, no model."""
import argparse
from contextlib import nullcontext
import ctypes
import json
import types
from unittest.mock import patch
import weakref
import torch
from b12x._lib import compiler
from b12x.gemm import bf16_gemv
from b12x.preparation import PreparationSession, PreparedCall
from vllm.v1.worker.gpu.model_runner import GPUModelRunner
from vllm.v1.worker.gpu.cudagraph_utils import CudaGraphManager
from vllm.v1.worker.workspace import init_workspace_manager, current_workspace_manager, reset_workspace_manager


@torch.inference_mode()
def main():
    p = argparse.ArgumentParser(); p.add_argument('--device-spelling', choices=('unindexed', 'indexed'), required=True)
    a = p.parse_args()
    import importlib
    helper = importlib.import_module('vllm.v1.worker.gpu._b12x_postcapture_heap')
    torch.cuda.init(); index = torch.cuda.current_device(); torch.manual_seed(17)
    device = torch.device('cuda' if a.device_spelling == 'unindexed' else f'cuda:{index}')
    init_workspace_manager(device)
    workspace = current_workspace_manager(); upload, = workspace.get_simultaneous(((1024**2,), torch.uint8))
    source = torch.randn(2, 2048, device=device, dtype=torch.bfloat16)
    weight = torch.randn(96, 2048, device=device, dtype=torch.bfloat16)
    pinned = torch.ones(1024**2, dtype=torch.uint8, pin_memory=True)
    plan = bf16_gemv.plan(bf16_gemv.query_from_call(source, weight))
    request = plan.request(name='postcapture-probe', prepare_call=lambda state: PreparedCall(run=lambda: state.run(source, weight)))
    libc = helper.libc_api(); libc.malloc.argtypes = (ctypes.c_size_t,); libc.malloc.restype = ctypes.c_void_p
    blocks = []; guards = []; retired = []; references = []; captured_pointers = []; output = None
    graph = torch.cuda.CUDAGraph(); host_graph = torch.cuda.CUDAGraph()
    class Garbage:
        def __init__(self): self.cycle = self
        def __del__(self):
            for number in retired:
                pointer = blocks[number]
                if pointer is not None: libc.free(pointer); blocks[number] = None
    class Manager:
        def __init__(self):
            self.calls = 0; self._graphs_captured = False; self._capture_descs = {'fixture': [True]}
        needs_capture = CudaGraphManager.needs_capture
        def capture(self, *args, **kwargs):
            nonlocal output
            self.calls += 1
            with session.capture(), torch.cuda.graph(graph):
                output = bf16_gemv.mm(source, weight, plan=plan)
            with torch.cuda.graph(host_graph): upload.copy_(pinned, non_blocking=True)
            captured_pointers.append((source.data_ptr(),weight.data_ptr(),output.data_ptr(),pinned.data_ptr(),upload.data_ptr()))
            # Synthetic CPU owners die at the REAL capture context's existing
            # unfreeze/collect, leaving free interior pages behind live guards.
            for number in range(8192):
                pointer = libc.malloc(65536)
                if not pointer: raise MemoryError('bounded CPU fixture failed')
                blocks.append(pointer); ctypes.memset(pointer, 37, 65536)
                (guards if number%64 == 0 or number == 8191 else retired).append(number)
            garbage = Garbage(); references.append(weakref.ref(garbage)); del garbage
            assert references[-1]() is not None
            self._graphs_captured = True
    manager = Manager(); resets = []
    runner = types.SimpleNamespace(cache_config=types.SimpleNamespace(kv_cache_memory_bytes=17*1024**3), device=device,
        cudagraph_manager=manager, model_state=types.SimpleNamespace(supports_mm_inputs=False),
        lora_config=None, maybe_setup_dummy_loras=lambda config:nullcontext(), model=None, input_buffers=None,
        intermediate_tensors=None, block_tables=None, attn_groups=[], kv_cache_config=None, pcp_manager=None,
        use_aux_hidden_state_outputs=False, speculator=None, adaptive_verification=None,
        kv_connector=types.SimpleNamespace(reset_capture_state=lambda:resets.append(True)))
    with PreparationSession(device=device, autotune=False, compile_workers=1) as session:
        session.prepare((request,))
        try:
            class CapturedObservation(Exception): pass
            records = []; original_emit = helper.emit
            def retain_record(row): original_emit(row); records.append(row)
            def forbidden_trim(*args): raise AssertionError('terminal observer called malloc_trim')
            real_api = helper.libc_api
            def observed_api():
                api = real_api(); api.malloc_trim = forbidden_trim; return api
            with patch.object(helper,'emit',side_effect=retain_record), patch.object(helper,'libc_api',side_effect=observed_api), patch.object(helper,'terminal_hold',side_effect=CapturedObservation):
                try: GPUModelRunner.capture_model(runner)
                except CapturedObservation: pass
                else: raise AssertionError('terminal observer fell through')
            assert len(records)==1 and records[0]['phase']=='observe'
            result = records[0]['result']
            assert manager.calls == 1 and resets == [True] and workspace.is_locked()
            assert manager.needs_capture() and manager._graphs_captured is True
            assert references[0]() is None
            pointers = captured_pointers[0]
            assert pointers == (source.data_ptr(),weight.data_ptr(),output.data_ptr(),pinned.data_ptr(),upload.data_ptr())
            assert all(ctypes.string_at(blocks[number],16) == b'%'*16 for number in guards)
            def forbidden(*args, **kwargs): raise AssertionError('replay called compiler or loader')
            with patch.object(compiler, 'compile', forbidden), patch.object(compiler, '_load_cute_compile_from_disk', forbidden):
                for number in (3,7,11):
                    pinned.fill_(number); upload.zero_(); host_graph.replay()
                    source.copy_(torch.randn_like(source)); output.fill_(float('nan')); graph.replay(); torch.cuda.synchronize()
                    assert torch.equal(upload, torch.full_like(upload,number))
                    assert torch.equal(pinned, torch.full_like(pinned,number))
                    torch.testing.assert_close(output,(source.float()@weight.float().T).bfloat16(),rtol=2e-2,atol=2e-2)
            assert pointers == (source.data_ptr(),weight.data_ptr(),output.data_ptr(),pinned.data_ptr(),upload.data_ptr())
            print(json.dumps(dict(device=str(device), original_capture_method=True, original_capture_metric=result,
                existing_gc_collected_fixture=True, fixture_bytes=8192*65536, live_CPU_guards_preserved=True,
                workspace_locked=True, live_pinned_graph_replays=3, prepared_b12x_graph_replays=3,
                pointers_preserved_across_observation=True, compiler_and_loader_forbidden=True,
                terminal_observation=True, trim_forbidden=True, reclamation_qualified=False,
                checkpoint_loaded=False, server_loaded=False)), flush=True)
        finally:
            graph.reset(); host_graph.reset()
            for number, pointer in enumerate(blocks):
                if pointer is not None: libc.free(pointer); blocks[number] = None
    reset_workspace_manager()


if __name__ == '__main__': main()
