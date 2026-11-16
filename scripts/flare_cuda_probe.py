"""Small compile/capture/replay probe, not full-model numerical qualification."""
import json
import subprocess

from ignition import runtime_patches

runtime_patches.apply()

import torch

assert torch.__version__ == "2.14.1+cu132", torch.__version__
assert torch.cuda.get_device_capability() == (12, 1)
torch.manual_seed(1234)
x = torch.randn(1024, 1024, device="cuda", dtype=torch.float32)
y = torch.randn_like(x)


@torch.compile(fullgraph=True)
def forward(a, b):
    return a * b + a


expected = x * y + x
stream = torch.cuda.Stream()
stream.wait_stream(torch.cuda.current_stream())
with torch.cuda.stream(stream):
    for _ in range(3):
        actual = forward(x, y)
torch.cuda.current_stream().wait_stream(stream)
torch.testing.assert_close(actual, expected)
graph = torch.cuda.CUDAGraph()
with torch.cuda.graph(graph):
    actual = forward(x, y)
for _ in range(3):
    graph.replay()
torch.cuda.synchronize()
torch.testing.assert_close(actual, expected)
print(json.dumps({"torch": torch.__version__, "cuda": torch.version.cuda,
                  "gpu": torch.cuda.get_device_name(), "capability": [12, 1],
                  "driver": subprocess.check_output(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"], text=True).strip(),
                  "compile_capture_replay": "passed",
                  "full_model_qualification": "not_run"}, indent=2))
