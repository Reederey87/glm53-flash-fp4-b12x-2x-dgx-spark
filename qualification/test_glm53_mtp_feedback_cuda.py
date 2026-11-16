"""Checkpoint MTP feedback component bounds under compiled native replay.

This isolates arithmetic on matched operands. It does not execute the draft
attention/MoE body, target verification or accepted-prefix cache transaction.
"""
import ast
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import time

import pytest
import torch
from safetensors import safe_open

from glm53_mtp_feedback_prefix import feedback

pytestmark = pytest.mark.skipif(os.environ.get('FLARE_RUN_CUDA_TESTS') != '1',
                               reason='requires an explicitly assigned Spark GPU')


def verify_prefix():
    manifest = json.loads(Path(__file__).with_name('glm53_mtp_feedback_provenance.json').read_text())
    source = Path(os.environ['FLARE_PINNED_SOURCE']) / manifest['source']
    assert hashlib.sha256(source.read_bytes()).hexdigest() == manifest['source_sha256']
    tree = ast.parse(source.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'PreparedMTP')
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '__call__')
    copied = ast.parse(Path(__file__).with_name('glm53_mtp_feedback_prefix.py').read_text()).body[-1]
    assert isinstance(copied, ast.FunctionDef) and copied.name == 'feedback'
    assert ast.dump(copied.args) == ast.dump(method.args)
    count = manifest['prefix_statement_count']
    assert isinstance(method.body[count], ast.If)
    assert len(copied.body) == count + 1
    assert [ast.dump(n) for n in copied.body[:-1]] == [ast.dump(n) for n in method.body[:count]]
    assert ast.dump(copied.body[-1]) == ast.dump(ast.parse('return embedded, joined, residual, normalized').body[0])


def norm_reference(source, weight, eps):
    value = source.double()
    normalized = value * torch.rsqrt(value.square().mean(-1, keepdim=True) + eps)
    return (normalized.bfloat16().double() * weight.double()).bfloat16()


def check_norm(actual, expected):
    assert torch.isfinite(actual).all()
    ulps = (actual.view(torch.int16).int() - expected.view(torch.int16).int()).abs()
    assert ulps.max() <= 2, int(ulps.max())
    return int(ulps.max())


@pytest.mark.parametrize('capacity', [1, 4, 16, 4096])
@torch.no_grad()
def test_checkpoint_mtp_feedback(capacity, record_property):
    from ignition.components.embedding import PreparedEmbedding
    from ignition.components.linear import UnquantizedProjection
    from ignition.components.parallel import TensorParallelShard
    from ignition.preparation.checkpoint import inspect_indexed_checkpoint
    from ignition.preparation.compilation import compile_forward
    from ignition.preparation.execution import GraphSignature, PreparedExecution
    from ignition.preparation.tuning import RecordedPreparationSession
    from ignition.recipes.glm53.weights import GlmWeightLoader, TEXT_PREFIX

    verify_prefix()
    assert torch.cuda.device_count() == 1 and torch.cuda.get_device_capability() == (12, 1)
    torch.cuda.set_device(0)
    device = torch.device('cuda:0')
    rank = int(os.environ['FLARE_TEST_RANK']); assert rank in (0, 1)
    manifest = inspect_indexed_checkpoint(Path(os.environ['FLARE_GLM53_SNAPSHOT']))
    prefix = f'{TEXT_PREFIX}.layers.45'
    names = {'embedding': f'{TEXT_PREFIX}.embed_tokens.weight',
             **{key: f'{prefix}.{key}.weight' for key in ('enorm', 'hnorm', 'eh_proj', 'input_layernorm')}}
    raw = {}
    for key, name in names.items():
        with safe_open(str(manifest.snapshot / manifest.tensors[name].shard), framework='pt') as f:
            raw[key] = f.get_tensor(name).clone()
        assert raw[key].dtype == torch.bfloat16 and torch.isfinite(raw[key]).all()
    with GlmWeightLoader(manifest, device, shard=TensorParallelShard(rank, 2),
                         prefixes=tuple(names.values())) as loader:
        weights = {key: loader.load_tensor(name) for key, name in names.items()}
        assert loader._session.torch_copy_bytes == 0
    for key in weights:
        assert torch.equal(weights[key].cpu().view(torch.int16), raw[key].view(torch.int16))
    assert weights['eh_proj'].shape == (4096, 8192)
    eps = json.loads((manifest.snapshot / 'config.json').read_text())['text_config']['rms_norm_eps']
    ids = torch.zeros(capacity, dtype=torch.int64, device=device)
    positions = torch.zeros_like(ids)
    hidden = torch.zeros((capacity, 4096), dtype=torch.bfloat16, device=device)
    live = torch.ones(1, dtype=torch.int32, device=device)
    metadata = SimpleNamespace(token_ids=ids, hidden=hidden, num_tokens=live,
                               indexed=SimpleNamespace(positions=positions))
    outputs = [torch.empty((capacity, width), dtype=torch.bfloat16, device=device)
               for width in (4096, 8192, 4096, 4096)]
    graph = torch.cuda.CUDAGraph()
    worker = None
    try:
        with RecordedPreparationSession(device=device, checkpoint='glm53-mtp-feedback',
                workload_schema='checkpoint-mtp-feedback-v1', numerical_policy='default',
                native_dense_activations=True, compile_workers=2) as session:
            owner = SimpleNamespace(weights=SimpleNamespace(tensors=weights), eps=eps)
            owner.embedding = PreparedEmbedding(weights['embedding'], ids, outputs[0],
                num_rows=live, session=session, name='feedback.embedding').functional(session=session, dynamic_inputs=True)
            owner.projection = UnquantizedProjection(outputs[1], weights['eh_proj'], outputs[2],
                session=session, name='feedback.eh_proj').functional(session=session)
            def forward():
                for target, value in zip(outputs, feedback(owner, metadata), strict=True):
                    target.copy_(value)
            session.tune()
            call = compile_forward(forward)
            call()
            torch.cuda.synchronize()
            stream = torch.cuda.Stream(device=device)
            stream.wait_stream(torch.cuda.current_stream(device))
            with session.capture(), torch.cuda.graph(graph, stream=stream):
                call()
            session.freeze()
            signature = (GraphSignature('prefill', 1, capacity) if capacity == 4096 else
                         GraphSignature('speculative', 4, 4) if capacity == 16 else
                         GraphSignature('decode', capacity, 1))
            control = {'frame_index': torch.zeros(1, dtype=torch.int32, device=device),
                       'submission_sequence': torch.zeros(1, dtype=torch.int64, device=device),
                       'completion_records': torch.zeros((2, 4, 32), dtype=torch.int64, device=device)}
            bundle = PreparedExecution(device=0, graphs={'feedback': graph}, signatures={'feedback': signature},
                buffers=control, resources=(owner, metadata, weights, outputs, session, call, stream))
            worker = bundle.start_executor()
            generator = torch.Generator(device=device).manual_seed(53117 + capacity)
            oracle_weight = raw['eh_proj'].to(device=device, dtype=torch.float64)
            norm_weights = {key: raw[key].to(device) for key in ('enorm', 'hnorm', 'input_layernorm')}
            for case, gain, count in (('normal', 1., capacity), ('small', .001, capacity),
                                      ('large', 1000., capacity), ('partial', 1., max(1, capacity // 2)),
                                      ('empty', 1., 0)):
                ids.copy_(torch.randint(0, weights['embedding'].shape[0], ids.shape, generator=generator, device=device))
                offset = {'normal': 0, 'small': 1, 'large': 255, 'partial': 0, 'empty': 1}[case]
                positions.copy_((torch.arange(capacity, device=device) + offset) % 257)
                live.fill_(count)
                hidden.normal_(generator=generator).mul_(gain)
                hidden[count:].zero_()
                saved = (ids.clone(), positions.clone(), hidden.clone(), live.clone())
                expected_embed = raw['embedding'][ids.cpu()].to(device)
                expected_embed[count:].zero_()
                expected_embed.masked_fill_((positions == 0)[:, None], 0)
                expected_joined = torch.cat((norm_reference(expected_embed, norm_weights['enorm'], eps),
                                             norm_reference(hidden, norm_weights['hnorm'], eps)), dim=1)
                for repetition in range(5):
                    for value in outputs:
                        value.fill_(float('nan'))
                    torch.cuda.synchronize()
                    before = torch.cuda.memory_stats()
                    ticket = worker.submit(bundle.graph_indices['feedback'], [])
                    assert ticket is not None
                    deadline = time.monotonic() + 120
                    completion = worker.poll()
                    while completion is None and time.monotonic() < deadline:
                        time.sleep(.001); completion = worker.poll()
                    assert completion is not None and completion.fence == ticket
                    after = torch.cuda.memory_stats()
                    for key in ('allocation.all.allocated', 'allocation.all.freed',
                                'segment.all.allocated', 'segment.all.freed'):
                        assert before[key] == after[key], key
                    torch.testing.assert_close(outputs[0], expected_embed, rtol=0, atol=0)
                    joined_ulps = check_norm(outputs[1], expected_joined)
                    expected_projection = (outputs[1].double() @ oracle_weight.T).bfloat16()
                    assert torch.isfinite(outputs[2]).all()
                    torch.testing.assert_close(outputs[2], expected_projection, rtol=.01, atol=.01)
                    final_ulps = check_norm(outputs[3], norm_reference(outputs[2], norm_weights['input_layernorm'], eps))
                    for value, original in zip((ids, positions, hidden, live), saved, strict=True):
                        assert torch.equal(value, original)
                    print(json.dumps({'rank': rank, 'capacity': capacity, 'case': case, 'rep': repetition,
                        'joined_max_ulps': joined_ulps, 'normalized_max_ulps': final_ulps,
                        'projection_max_abs_error': float((outputs[2].float() - expected_projection.float()).abs().max())}), flush=True)
            worker.close(); worker = None
            graph.reset()
        for key in weights:
            assert torch.equal(weights[key].cpu().view(torch.int16), raw[key].view(torch.int16))
        record_property('scope', 'checkpoint feedback prefix component references; excludes MLA/MoE and state transaction')
    finally:
        if worker is not None:
            worker.close()
        graph.reset()
