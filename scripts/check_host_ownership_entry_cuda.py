"""Tiny real API probe in a disposable pinned image, with no checkpoint/server."""
import importlib.util
import json
from pathlib import Path
import time
import types
import torch

path = Path('/usr/local/lib/python3.12/dist-packages/vllm/v1/worker/_b12x_host_ownership_entry.py')
spec = importlib.util.spec_from_file_location('ownership_probe', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
torch.cuda.init()
index = torch.cuda.current_device()
results = []


def hold(seconds):
    assert seconds == 120
    raise StopIteration('probe reached intentional hold')


module.time = types.SimpleNamespace(time_ns=time.time_ns, sleep=hold)
for spelling in ('cuda', f'cuda:{index}'):
    worker = types.SimpleNamespace(device=torch.device(spelling))
    pinned = torch.ones(1024 * 1024, dtype=torch.uint8, pin_memory=True)
    value = torch.ones(16, device=worker.device)
    stream = torch.cuda.Stream()
    stream.wait_stream(torch.cuda.current_stream())
    with torch.cuda.stream(stream):
        for _ in range(3):
            output = value + 1
    torch.cuda.current_stream().wait_stream(stream)
    graph = torch.cuda.CUDAGraph()
    with torch.cuda.graph(graph):
        output = value + 1
    pointers = value.data_ptr(), output.data_ptr(), pinned.data_ptr()
    @module.observe_before_warmup
    def warmup(owner):
        raise AssertionError('original warmup must not execute')
    try:
        warmup(worker)
    except StopIteration as error:
        assert str(error) == 'probe reached intentional hold'
    else:
        raise AssertionError('diagnostic returned into serving')
    record = module.snapshot(worker)
    assert record['device_index'] == index
    assert record['boundary'] == 'pre-warmup'
    assert record['pinned']['active_bytes.current'] >= pinned.numel()
    assert record['pinned']['allocated_bytes.current'] >= record['pinned']['active_bytes.current']
    assert record['processes'] and record['host']['MemAvailable'] > 2 * 1024**3
    value.fill_(7)
    graph.replay()
    assert torch.equal(output, torch.full_like(output, 8))
    assert pointers == (value.data_ptr(), output.data_ptr(), pinned.data_ptr())
    results.append(dict(device=spelling, api_counters_valid=True, original_graph_preserved=True,
                        intentional_hold_reached=True))
    del graph, value, output, pinned
print(json.dumps(dict(pytorch=torch.__version__, checks=results, checkpoint_loaded=False, server_loaded=False)))
