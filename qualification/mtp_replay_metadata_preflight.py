"""CPU-only fresh-process check of Flare's real forward metadata serializer.

Synthetic operations isolate observer serialization; GPU preparation and model
numerics remain separate gates. No CUDA context or model weights are needed.
"""
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace

import torch

from mtp_replay_forward import (InputObservation, MTPReplayForward,
    OutputObservation, ProjectionObservation, SelectionObservation)


@dataclass
class Selection:
    value: torch.Tensor


class Scale:
    def __call__(self, value):
        return value * 2


class Indexer:
    def __init__(self):
        self.forward = SelectionObservation(self.forward, Selection(torch.zeros(2)))

    def forward(self, source):
        return source, Selection(source + 1)


class Operation:
    def __init__(self, stages):
        self.projection = ProjectionObservation(Scale(), stages)
        self.attention_reduce = OutputObservation(Scale(), stages['attention'])
        self.moe = InputObservation(Scale(), stages['moe_input'])
        self.mlp_reduce = OutputObservation(Scale(), stages['moe_reduced'])
        self.indexer = Indexer()

    def __call__(self, metadata):
        source = self.projection(metadata.hidden)
        self.indexer.forward(source)
        result = self.mlp_reduce(self.moe(self.attention_reduce(source)))
        return result, result + 1


def verify(path):
    from ignition.preparation.forward_metadata import loads
    forwards = loads(Path(path).read_bytes())
    assert set(forwards) == {False, True}
    for cache_only, forward in forwards.items():
        assert type(forward) is MTPReplayForward
        assert type(forward.operation.projection) is ProjectionObservation
        assert type(forward.operation.attention_reduce) is OutputObservation
        assert type(forward.operation.moe) is InputObservation
        assert type(forward.operation.indexer.forward) is SelectionObservation
        assert forward.operation.indexer.forward.operation.__self__ is forward.operation.indexer
        assert forward.stages is forward.operation.projection.stages
        forward()  # FakeTensor execution calls every deserialized observer.
        assert forward.output.shape == (2,)
    assert not torch.cuda.is_initialized()
    print(json.dumps({'forward_metadata_roundtrip': True, 'fresh_process': True,
        'both_cache_paths': True, 'all_observers_called': True,
        'bound_method_cycle_and_aliases_preserved': True, 'cuda_initialized': False}))


def main():
    from ignition.preparation.forward_metadata import dumps
    forwards = {}
    captured = []

    def cpu_backend(graph, example_inputs):
        # This only checks Dynamo's treatment of the synthetic observer owners.
        # GPU qualification still uses production AOT compilation with no fallback.
        assert any(node.op in ('call_function', 'call_method') for node in graph.graph.nodes)
        captured.append(graph)
        return graph.forward

    for cache_only in (False, True):
        stages = {key: torch.zeros(2) for key in ('joined', 'feedback_projection',
            'attention', 'moe_input', 'moe_reduced', 'logits')}
        forward = MTPReplayForward(Operation(stages), SimpleNamespace(hidden=torch.ones(2)),
                                   cache_only, torch.zeros(2), stages)
        forward()
        torch.testing.assert_close(forward.output, torch.full((2,), 1. if cache_only else 16.))
        torch.testing.assert_close(stages['joined'], torch.ones(2))
        torch.testing.assert_close(stages['feedback_projection'], torch.full((2,), 2.))
        torch.testing.assert_close(stages['attention'], torch.full((2,), 4.))
        torch.testing.assert_close(stages['moe_input'], torch.full((2,), 4.))
        torch.testing.assert_close(stages['moe_reduced'], torch.full((2,), 16.))
        torch.testing.assert_close(forward.operation.indexer.forward.storage.value, torch.full((2,), 3.))
        forward.output.fill_(float('nan'))
        torch.compile(forward, backend=cpu_backend, fullgraph=True)()
        torch.testing.assert_close(forward.output, torch.full((2,), 1. if cache_only else 16.))
        forwards[cache_only] = forward
    assert len(captured) == 2
    print(json.dumps({'cpu_fullgraph_traces': len(captured),
                     'scope': 'synthetic observer tracing only; no GPU compilation'}), flush=True)
    with tempfile.TemporaryDirectory(prefix='mtp-metadata-') as temporary:
        path = Path(temporary) / 'metadata.pkl'
        path.write_bytes(dumps(forwards))
        subprocess.run([sys.executable, '-c',
            'from mtp_replay_metadata_preflight import verify; import sys; verify(sys.argv[1])',
            str(path)], check=True)
    assert not torch.cuda.is_initialized()


if __name__ == '__main__':
    # Importable classes must retain the same module identity in the child.
    from mtp_replay_metadata_preflight import main
    main()
