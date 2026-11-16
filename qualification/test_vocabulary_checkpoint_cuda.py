# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-FileCopyrightText: Copyright (c) 2026 Flare community contributors
# SPDX-License-Identifier: Apache-2.0
"""Checkpoint MXFP8 vocabulary projection against FP64 with native TP2 RoCE replay."""
import ast
import hashlib
import json
import os
import socket
import time
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlsplit
import pytest
import torch
import torch.distributed as dist
from vocabulary_checkpoint_reference import load_checkpoint_head, checkpoint_reference

pytestmark = pytest.mark.skipif(os.environ.get("FLARE_RUN_ROCE_TESTS") != "1",
                               reason="requires both assigned Spark hosts")

@torch.no_grad()
def _rank(rank, world, rendezvous, vocab, indexed=False, output_dtype=torch.bfloat16):
    from ignition.components.vocabulary import PreparedVocabularyProjection
    from ignition.preparation.collectives import (
        CollectivePreparation,
        create_roce_runtime,
        warmup_wait,
    )
    from ignition.preparation.compilation import compile_forward
    from ignition.preparation.execution import GraphSignature, PreparedExecution
    from ignition.preparation.tuning import RecordedPreparationSession

    torch.cuda.set_device(0)
    device = torch.device("cuda:0")
    dist.init_process_group("gloo", init_method=rendezvous, rank=rank, world_size=world,
                            timeout=timedelta(minutes=15))
    group = dist.group.WORLD
    coordinator = CollectivePreparation(group, timeout=timedelta(minutes=15))
    assert coordinator.spans_hosts
    hidden, capacity = 4096, 16
    width = (vocab + world * 64 - 1) // (world * 64) * 64
    torch.manual_seed(42)
    weight, reference_weight = load_checkpoint_head(rank, world, device)
    valid_columns = min(width, vocab - rank * width)
    assert valid_columns == width == 77440
    seed = torch.randn(capacity, hidden, dtype=torch.bfloat16, device=device) * .125
    source = seed.clone()
    local = torch.empty(capacity, width, dtype=output_dtype, device=device)
    sample_capacity = 2 * capacity if indexed else capacity
    output = torch.empty(sample_capacity, vocab, dtype=output_dtype, device=device)
    indices = torch.zeros(sample_capacity, dtype=torch.int64, device=device) if indexed else None
    runtime = create_roce_runtime(group, device, max_tokens=1, pipe_tokens=1,
        hidden_size=hidden, gather_bytes=capacity * width * output.element_size())
    graphs, heads, compiled = {}, {}, {}
    control = {"frame_index": torch.zeros(1, dtype=torch.int32, device=device),
               "submission_sequence": torch.zeros(1, dtype=torch.int64, device=device),
               "completion_records": torch.zeros((2, 4, 32), dtype=torch.int64, device=device)}
    worker = None
    try:
        with RecordedPreparationSession(device=device, checkpoint="vocabulary-test",
                workload_schema="column-gather-v1", numerical_policy="default", coordinator=coordinator,
                native_dense_activations=True, compile_workers=2) as session:
            for rows in (16, 4, 1):
                result = output if indexed else output[:rows]
                heads[rows] = PreparedVocabularyProjection(source[:rows], weight, local[:rows], result,
                    runtime=runtime, session=session, coordinator=coordinator, name=f"head{rows}", row_indices=indices)
                assert heads[rows].projection.activation_mode == "a16"
            session.tune()
            stream = torch.cuda.Stream(device=device)
            pool = torch.cuda.graph_pool_handle()
            for rows, head in heads.items():
                compiled[rows] = compile_forward(lambda head=head, rows=rows: head(source[:rows]))
                with warmup_wait(runtime, coordinator):
                    compiled[rows]()
                torch.cuda.synchronize(device)
                stream.wait_stream(torch.cuda.current_stream(device))
                graph = torch.cuda.CUDAGraph()
                with runtime.capture(stream=stream), session.capture(), torch.cuda.graph(graph, stream=stream, pool=pool):
                    compiled[rows]()
                graphs[f"head{rows}"] = graph
            session.freeze()
            bundle = PreparedExecution(device=0, graphs=graphs,
                signatures={f"head{rows}": GraphSignature("decode", rows, 1) for rows in heads},
                buffers=control,
                resources=(heads, compiled, runtime, session, stream, pool, weight))
            worker = bundle.start_executor()
            for index, (rows, repetitions) in enumerate(((1, 13), (4, 8), (16, 8), (1, 31), (4, 17), (16, 17))):
                source.copy_(seed + index * .03125)
                expected = checkpoint_reference(source[:rows], reference_weight, group, world, output_dtype)
                if indexed:
                    indices.copy_((torch.arange(sample_capacity, device=device) * 3 + index) % rows)
                    expected = expected[indices]
                output.fill_(float("nan"))
                torch.cuda.synchronize(device)
                before = torch.cuda.memory_stats(device)
                dist.barrier(group=group)
                for _ in range(repetitions):
                    ticket = worker.submit(bundle.graph_indices[f"head{rows}"], [])
                    assert ticket is not None
                    deadline = time.monotonic() + 120
                    completion = worker.poll()
                    while completion is None and time.monotonic() < deadline:
                        time.sleep(.001)
                        completion = worker.poll()
                    assert completion is not None and completion.fence == ticket
                after = torch.cuda.memory_stats(device)
                for key in ("allocation.all.allocated", "allocation.all.freed",
                            "segment.all.allocated", "segment.all.freed"):
                    assert before[key] == after[key]
                result = output if indexed else output[:rows]
                print(json.dumps({"rank": rank, "indexed": indexed, "rows": rows,
                    "repetitions": repetitions, "max_abs_error": (result.float()-expected.float()).abs().max().item(),
                    "finite": bool(torch.isfinite(result).all())}), flush=True)
                assert torch.isfinite(result).all()
                torch.testing.assert_close(result, expected,
                    rtol=.016 if output_dtype == torch.bfloat16 else 2e-5,
                    atol=.002 if output_dtype == torch.bfloat16 else 2e-5)
                selected_local = local[:rows] if indices is None else local[:rows][indices]
                torch.testing.assert_close(result[:, rank * width:rank * width + valid_columns],
                                           selected_local[:, :valid_columns], rtol=0, atol=0)
                if not indexed and rows < capacity:
                    assert output[rows:].isnan().all()
                dist.barrier(group=group)
            worker.close()
            worker = None
            for graph in graphs.values():
                graph.reset()
    finally:
        if worker is not None:
            worker.close()
        for graph in graphs.values():
            graph.reset()
        runtime.close()
        dist.destroy_process_group()

@pytest.mark.parametrize("indexed", [False, True])
def test_checkpoint_vocabulary_replay(indexed, record_property):
    from ignition.preparation.host_ranks import _use_interface
    source = Path(os.environ["FLARE_PINNED_SOURCE"]) / "tests/components/test_vocabulary_cuda.py"
    adaptation = json.loads(Path(__file__).with_name("vocabulary_checkpoint_adaptation.json").read_text())
    assert hashlib.sha256(source.read_bytes()).hexdigest() == adaptation["source_sha256"]
    text = source.read_text()
    node = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == "_rank")
    expected = "\n".join(text.splitlines()[min([node.lineno]+[d.lineno for d in node.decorator_list])-1:node.end_lineno])
    for old, new in adaptation["exact_substitutions"]:
        assert expected.count(old) == 1
        expected = expected.replace(old, new, 1)
    actual = next(n for n in ast.parse(Path(__file__).read_text()).body if isinstance(n, ast.FunctionDef) and n.name == "_rank")
    assert ast.dump(actual) == ast.dump(ast.parse(expected).body[0])
    rank = int(os.environ["FLARE_TEST_RANK"])
    assert rank in (0, 1) and torch.cuda.device_count() == 1
    rendezvous = os.environ["FLARE_TEST_RENDEZVOUS"]
    address = urlsplit(rendezvous)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as route:
        route.connect((address.hostname, address.port))
        _use_interface(route.getsockname()[0])
    _rank(rank, 2, rendezvous, 154880, indexed)
    record_property("reference", "raw checkpoint E4M3 times UE8M0, FP64 dot, Gloo gather")
    record_property("activation_mode", "a16")
