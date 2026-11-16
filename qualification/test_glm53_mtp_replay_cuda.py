"""Checkpoint draft-layer and absorption replay on two single-GPU Spark hosts.

Python and Rust replay share prepared operators and initial state. This tests
composition and native replay, not independent whole-model mathematics.
"""
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import socket
from types import SimpleNamespace
import time
from urllib.parse import urlsplit

import pytest
import torch
import torch.distributed as dist

pytestmark = pytest.mark.skipif(os.environ.get('FLARE_RUN_ROCE_TESTS') != '1',
                               reason='requires both assigned Spark hosts')


@pytest.mark.parametrize('mode,capacity,cache_only', [
    ('decode', 1, False), ('decode', 4, False),
    ('decode', 16, True), ('prefill', 128, True), ('prefill', 4096, True),
])
@torch.no_grad()
def test_checkpoint_mtp_replay(mode, capacity, cache_only, record_property):
    from ignition.components.parallel import TensorParallelShard
    from ignition.preparation.checkpoint import inspect_indexed_checkpoint
    from ignition.preparation.collectives import CollectivePreparation, create_roce_runtime, warmup_wait
    from ignition.preparation.compilation import compile_forward
    from ignition.preparation.execution import GraphSignature, PreparedExecution
    from ignition.preparation.scratch import ScratchArena
    from ignition.preparation.tuning import RecordedPreparationSession
    from ignition.recipes.glm53.mla import MLAState
    from ignition.recipes.glm53.model import create_model_tree
    from ignition.recipes.glm53.mtp import DraftMetadata, MTPScratch, PreparedMTP
    from ignition.recipes.glm53.weights import GlmWeightLoader, TEXT_PREFIX
    from layer_selection_reference import install_observer, matched_reference

    root = Path(os.environ['FLARE_PINNED_SOURCE'])
    assert hashlib.sha256((root / 'ignition/recipes/glm53/mtp.py').read_bytes()).hexdigest() == (
        '810b4dd738752f80e246e36a740519e191f146c8bee45cadfae525c15bf7fd02')
    rank = int(os.environ['FLARE_TEST_RANK']); assert rank in (0, 1)
    from ignition.preparation.host_ranks import _use_interface
    address = urlsplit(os.environ['FLARE_TEST_RENDEZVOUS'])
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as route:
        route.connect((address.hostname, address.port))
        _use_interface(route.getsockname()[0])
    record_property('gloo_interface', os.environ['GLOO_SOCKET_IFNAME'])
    assert torch.cuda.device_count() == 1 and torch.cuda.get_device_capability() == (12, 1)
    torch.cuda.set_device(0)
    device = torch.device('cuda:0')
    shard = TensorParallelShard(rank, 2)
    snapshot = Path(os.environ['FLARE_GLM53_SNAPSHOT'])
    manifest = inspect_indexed_checkpoint(snapshot)
    tree = create_model_tree(snapshot)
    with GlmWeightLoader(manifest, device, shard=shard, expert_activation='a16',
            prefixes=(f'{TEXT_PREFIX}.layers.45.', f'{TEXT_PREFIX}.embed_tokens.weight', 'lm_head.')) as loader:
        embedding = loader.load_tensor(f'{TEXT_PREFIX}.embed_tokens.weight')
        tree.model.language_model.embed_tokens.weight = torch.nn.Parameter(embedding, requires_grad=False)
        head = loader.load_linear('lm_head', rows=shard.partition(154880, alignment=64))
        mtp = loader.load_mtp(None)
        assert loader._session.torch_copy_bytes == 0
        assert mtp.mlp.experts.plan.activation.mode.value == 'a16'
        assert not mtp.mlp.experts_a4_prefill and mtp.draft_head is None
    weights = SimpleNamespace(tree=tree, shard=shard, head=head, mtp=mtp)
    batch = 1 if mode == 'prefill' else min(capacity, 4)
    width = capacity // batch
    count = 65 if capacity == 128 else capacity
    metadata = DraftMetadata(capacity, batch, 64, device)
    state = MLAState.allocate(256, 6, device, ring=12)
    persistent = {'latent_cache': state.cache, 'index_cache': state.index.cache, 'tail': state.index.tail}
    scratch = MTPScratch.allocate(capacity, 2, 64, mode, device, moe=not cache_only)
    # Immutable readbacks are separate from the forward's aliased scratch.
    output = torch.zeros((capacity, 4096), dtype=torch.bfloat16, device=device)
    stages = {name: torch.empty((capacity, size), dtype=torch.bfloat16, device=device)
              for name, size in [('joined', 8192), ('feedback_projection', 4096)]}
    if not cache_only:
        stages.update({name: torch.empty((capacity, size), dtype=torch.bfloat16, device=device)
                       for name, size in [('attention', 4096), ('moe_input', 4096),
                                          ('moe_reduced', 4096), ('logits', 154880)]})
    dist.init_process_group('gloo', init_method=os.environ['FLARE_TEST_RENDEZVOUS'],
                            rank=rank, world_size=2, timeout=timedelta(minutes=10))
    group = dist.group.WORLD
    coordinator = CollectivePreparation(group)
    runtime = create_roce_runtime(group, device, max_tokens=min(capacity, 128),
        pipe_tokens=capacity, hidden_size=4096, gather_bytes=capacity * 77440 * 2 if not cache_only else 4096)
    worker = None
    graph = torch.cuda.CUDAGraph()
    try:
        arena = ScratchArena(device)
        with RecordedPreparationSession(device=device, checkpoint='GLM-5.3-Flash-FP4-Local',
                workload_schema='checkpoint-mtp-replay-v1', numerical_policy='default',
                coordinator=coordinator, native_dense_activations=True, compile_workers=2) as session:
            session.register_scratch(arena)
            op = PreparedMTP(weights, state, metadata, mode=mode, session=session,
                name='checkpoint.mtp', workspace=arena, runtime=runtime, vocabulary_runtime=runtime,
                coordinator=coordinator, cache_only=cache_only, scratch=scratch)
            op.functional(session=session)
            projection = op.projection
            def project(source):
                stages['joined'].copy_(source)
                value = projection(source)
                stages['feedback_projection'].copy_(value)
                return value
            op.projection = project
            if not cache_only:
                install_observer(op, scratch.attention.index)
                attention_reduce, moe, mlp_reduce = op.attention_reduce, op.moe, op.mlp_reduce
                def reduce_attention(source):
                    value = attention_reduce(source)
                    stages['attention'].copy_(value)
                    return value
                def run_moe(source):
                    stages['moe_input'].copy_(source)
                    return moe(source)
                def reduce_moe(source):
                    value = mlp_reduce(source)
                    stages['moe_reduced'].copy_(value)
                    return value
                op.attention_reduce, op.moe, op.mlp_reduce = reduce_attention, run_moe, reduce_moe
            def forward():
                result = op(metadata)
                if cache_only:
                    output.copy_(metadata.hidden)
                else:
                    output.copy_(result[0])
                    stages['logits'].copy_(result[1])
            session.tune()
            arena.release_preparation()
            compiled = compile_forward(forward)
            with warmup_wait(runtime, coordinator):
                compiled()
            torch.cuda.synchronize()
            stream = torch.cuda.Stream(device=device)
            stream.wait_stream(torch.cuda.current_stream(device))
            with runtime.capture(stream=stream), session.capture(), torch.cuda.graph(graph, stream=stream):
                compiled()
            session.freeze()
            control = {'frame_index': torch.zeros(1, dtype=torch.int32, device=device),
                       'submission_sequence': torch.zeros(1, dtype=torch.int64, device=device),
                       'completion_records': torch.zeros((2, 4, 32), dtype=torch.int64, device=device)}
            signature = (GraphSignature('prefill', 1, capacity) if mode == 'prefill' else
                         GraphSignature('speculative', 4, 4) if capacity == 16 else
                         GraphSignature('decode', capacity, 1))
            bundle = PreparedExecution(device=0, graphs={'mtp': graph}, signatures={'mtp': signature},
                buffers=control, resources=(op, weights, metadata, state, scratch, stages, output,
                                            runtime, coordinator, session, arena, stream, compiled))
            worker = bundle.start_executor()
            generator = torch.Generator().manual_seed(534517 + capacity)
            ids = torch.randint(0, 154880, (batch, width), generator=generator).to(device)
            hidden = (torch.randn((batch, width, 4096), generator=generator) * .1).bfloat16().to(device)
            lengths = torch.full((batch,), width, dtype=torch.int64, device=device)
            if capacity == 128:
                lengths[0] = count
            tables = torch.arange(4 * 64, dtype=torch.int32, device=device).view(4, 64)
            state_rows = torch.arange(1, 5, dtype=torch.int64, device=device)[:, None].expand(4, 8).contiguous()
            slots = torch.arange(batch, dtype=torch.int64, device=device)
            for value in persistent.values():
                value.zero_()
            for step in range(3):
                starts = torch.full((batch,), step * count // batch, dtype=torch.int64, device=device)
                metadata.set(slots, lengths, starts, ids, hidden, tables, capacity=width, state_rows=state_rows)
                inputs = {key: getattr(metadata, key) for key in ('token_ids', 'hidden', 'num_tokens', 'output_indices')}
                inputs.update({f'indexed.{key}': getattr(metadata.indexed, key) for key in
                               ('positions', 'state_slots', 'query_start_loc', 'block_table', 'token_slots', 'requests')})
                input_before = {key: value.clone() for key, value in inputs.items()}
                for repetitions in (1, 4):
                    initial = {key: value.clone() for key, value in persistent.items()}
                    for _ in range(repetitions):
                        forward()
                    expected_output = output.clone()
                    expected_stages = {key: value.clone() for key, value in stages.items()}
                    expected_state = {key: value.clone() for key, value in persistent.items()}
                    for key, value in persistent.items():
                        value.copy_(initial[key])
                    for value in (output, *stages.values()):
                        value.fill_(float('nan'))
                    torch.cuda.synchronize()
                    dist.barrier(group=group)
                    before = torch.cuda.memory_stats()
                    for _ in range(repetitions):
                        ticket = worker.submit(bundle.graph_indices['mtp'], [])
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
                    if not cache_only:
                        expected_output, expected_stages = matched_reference(op, scratch.attention.index,
                            metadata.indexed, forward, persistent, initial, output, stages,
                            expected_output, expected_stages, repetitions,
                            os.environ['FLARE_SELECTION_RECEIPT'] + f'-mtp-{capacity}.jsonl')
                    for key, value in persistent.items():
                        assert torch.equal(value, expected_state[key]), key
                    for key, value in inputs.items():
                        assert torch.equal(value, input_before[key]), key
                    assert not state.index.tail[0].count_nonzero()
                    for key, value in stages.items():
                        assert torch.isfinite(value).all(), key
                        torch.testing.assert_close(value, expected_stages[key], rtol=0, atol=0, msg=key)
                    assert torch.isfinite(output).all()
                    torch.testing.assert_close(output, expected_output, rtol=0, atol=0)
                    gathered = [None, None]
                    dist.all_gather_object(gathered, output.cpu(), group=group)
                    assert torch.equal(gathered[0], gathered[1])
                    print(json.dumps({'rank': rank, 'mode': mode, 'capacity': capacity,
                        'cache_only': cache_only, 'step': step, 'repetitions': repetitions,
                        'state_and_stages_exact': True}), flush=True)
            worker.close(); worker = None
            graph.reset()
        record_property('scope', 'same-operator Python/Rust draft and absorption replay; component references separate')
    finally:
        if worker is not None:
            worker.close()
        graph.reset()
        runtime.close()
        dist.destroy_process_group()
