# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-FileCopyrightText: Copyright (c) 2026 Flare community contributors
# SPDX-License-Identifier: Apache-2.0

"""Pinned upstream KDA reference, parameterized for deployed TP2/MTP-3 geometry.

Derived from Flare 5a4e867 tests/recipes/test_glm53_mtp_state_cuda.py.
Keep the upstream TP4/width6 control and all original numerical bounds.
These are per-rank operator tests, not a two-host collective qualification.
"""

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

from ignition.components.parallel import TensorParallelShard
from ignition.components.recurrent import DeltaMetadata
from ignition.preparation.checkpoint import inspect_indexed_checkpoint
from ignition.preparation.scratch import ScratchArena
from ignition.preparation.tuning import RecordedPreparationSession
from ignition.recipes.glm53.kda import KDARecords, KDAScratch, PreparedGlmKDA
from ignition.recipes.glm53.model import create_model_tree
from ignition.recipes.glm53.pool import ContinuationPool
from ignition.recipes.glm53.speculative import PreparedKDACommit, PreparedRound, convolution_regions
from ignition.recipes.glm53.weights import GlmWeightLoader, TEXT_PREFIX

pytestmark = pytest.mark.skipif(os.environ.get("FLARE_RUN_CUDA_TESTS") != "1",
                               reason="requires an explicitly assigned CUDA device")


@pytest.mark.parametrize("world,verify_width", [(2, 4), (4, 6)])
@torch.no_grad()
def test_learned_kda_verification_commits_each_prefix_before_plain_decode(
        world, verify_width, record_property, native_dense_activations=False):
    snapshot = Path(os.environ.get("FLARE_GLM53_SNAPSHOT",
        "/data/checkpoint-releases/GLM-5.3-Flash-NVFP4-MXFP8-CSF-QAD"))
    manifest = inspect_indexed_checkpoint(snapshot)
    module = create_model_tree(snapshot).model.language_model.layers[0].self_attn
    with GlmWeightLoader(manifest, "cuda:0", shard=TensorParallelShard(0, world),
                         prefixes=(f"{TEXT_PREFIX}.layers.0.self_attn.",)) as loader:
        weights = loader.load_attention(0)
    pool = ContinuationPool.allocate(("linear_attention",), world, 10, 1, "cuda:0", mtp=True)
    state = pool.decoder.layers[0]
    arena = ScratchArena("cuda:0")
    metas = {width: DeltaMetadata.allocate(1, "cuda:0", verification_columns=8) for width in (1, verify_width)}
    sources = {width: torch.zeros((width, 4096), dtype=torch.bfloat16, device="cuda:0") for width in metas}
    slots = torch.tensor([0], dtype=torch.int32, device="cuda:0")
    counts = torch.ones(1, dtype=torch.int32, device="cuda:0")
    op = PreparedRound.__new__(PreparedRound)
    op.owner = SimpleNamespace(pool=pool, requests=SimpleNamespace(capacity=1),
                              inputs=SimpleNamespace(row_slot_ids=slots,
                                  request_state_rows=torch.tensor([[1, 0, 0, 0, 0, 0, 0, 0]], device="cuda:0")))
    op.width, op.batch, op.rows = verify_width, 1, torch.arange(1, device="cuda:0")
    op.convolution_regions = convolution_regions(pool)
    records = KDARecords.allocate({0: weights}, state.recurrent.shape[0], state.recurrent.shape[1], "cuda:0")
    hidden = torch.zeros((verify_width, 4096), dtype=torch.bfloat16, device="cuda:0")
    verified_output = torch.empty_like(hidden)
    operators = {}
    with RecordedPreparationSession(device=torch.device("cuda:0"), checkpoint="glm53-mtp-state",
            workload_schema="glm-kda-prefix-v1", numerical_policy="default",
            native_dense_activations=native_dense_activations) as session:
        record_property("native_dense_activations", session.native_dense_activations)
        session.register_scratch(arena)
        for width in metas:
            operators[width] = PreparedGlmKDA(module, weights, sources[width],
                KDAScratch.allocate(width, 64 // world, "cuda:0"), state, metas[width],
                mode="decode", session=session, name=f"decode{width}", workspace=arena,
                records=records.layer(0) if width > 1 else None)
        op.kda_commit = PreparedKDACommit(pool, records, operators[verify_width].recurrent_plan,
            metas[verify_width].state_indices[:, 0], metas[verify_width].num_seqs, session=session, workspace=arena)
        for operator in operators.values():
            operator.functional(session=session)
        tuning_report = session.tune()
        selections = [{key: item[key] for key in ("name", "component", "config")}
                      for item in tuning_report["selections"]
                      if "input_proj" in item["name"] or "o_proj" in item["name"]]
        record_property("projection_selections", json.dumps(selections, allow_nan=False))
        arena.release_preparation()
        operators[1](sources[1], metas[1])
        for width, meta in metas.items():
            meta.query_start_loc.copy_(torch.tensor([0, width], dtype=torch.int32))
            meta.convolution_slots.fill_(1)
            # Verification reads the live row in column zero; plain decode writes it back there.
            meta.state_indices.copy_(torch.tensor([[1, 0, 0, 0, 0, 0, 0, 0]]))
            meta.num_seqs.fill_(1)
            meta.num_tokens.fill_(width)
        generator = torch.Generator(device="cuda:0").manual_seed(531)
        chain = torch.randn((verify_width + 1, 4096), generator=generator, device="cuda:0", dtype=torch.bfloat16) * .1
        state.recurrent.normal_(0, .01, generator=generator)
        state.convolution.normal_(0, .1, generator=generator)
        initial_r, initial_c = state.recurrent.clone(), state.convolution.clone()
        sources[verify_width].copy_(chain[:verify_width])
        verified_output.copy_(operators[verify_width](sources[verify_width], metas[verify_width], records=records.layer(0)))
        op.commit_state(slots.long(), counts, records, metas[verify_width], hidden)
        graph = torch.cuda.CUDAGraph()
        with session.capture(), torch.cuda.graph(graph):
            verified_output.copy_(operators[verify_width](sources[verify_width], metas[verify_width], records=records.layer(0)))
            op.commit_state(slots.long(), counts, records, metas[verify_width], hidden)
        session.freeze()
        # Each verified token's output matches decoding the tokens one at a time. Plain decode and verification
        # read different columns of an arbitrary convolution history, so this check starts from an empty one.
        plain = []
        state.recurrent.copy_(initial_r)
        state.convolution.zero_()
        for index in range(verify_width):
            sources[1].copy_(chain[index:index + 1])
            plain.append(operators[1](sources[1], metas[1]).clone())
        state.recurrent.copy_(initial_r)
        state.convolution.zero_()
        counts.fill_(1)
        graph.replay()
        torch.cuda.synchronize()
        verified = verified_output.float()
        expected = torch.cat(plain).float()
        relative = ((verified - expected).norm() / expected.norm()).item()
        # Recording rounds the recurrence to BF16 before the gated norm, as b12x's recording does.
        record_property("world", world)
        record_property("verification_width", verify_width)
        record_property("relative_l2", relative)
        print(f"KDA world={world} width={verify_width} relative_l2={relative}", flush=True)
        if relative >= 1e-2:
            from kda_diagnostics import diagnose

            diagnostic = diagnose(operators, sources, metas, records, state, chain,
                                  initial_r, initial_c, verify_width)
            encoded = json.dumps(diagnostic, allow_nan=False)
            record_property("stage_diagnostics", encoded)
            print(f"KDA diagnostics world={world} width={verify_width}: {encoded}", flush=True)
        assert relative < 1e-2, relative
        for accepted in range(1, verify_width + 1):
            state.recurrent.copy_(initial_r)
            state.convolution.copy_(initial_c)
            for index in range(accepted):
                sources[1].copy_(chain[index:index + 1])
                operators[1](sources[1], metas[1])
            expected_r, expected_c = state.recurrent[1].clone(), state.convolution[1, :, :3].clone()
            sources[1].copy_(chain[verify_width:])
            expected_output = operators[1](sources[1], metas[1]).clone()
            state.recurrent.copy_(initial_r)
            state.convolution.copy_(initial_c)
            counts.fill_(accepted)
            graph.replay()
            torch.cuda.synchronize()
            torch.testing.assert_close(state.recurrent[1], expected_r, rtol=.025, atol=.002)
            torch.testing.assert_close(state.convolution[1, :, :3], expected_c, rtol=.025, atol=.002)
            actual_output = operators[1](sources[1], metas[1])
            torch.testing.assert_close(actual_output, expected_output, rtol=.025, atol=.005)
