# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-FileCopyrightText: Copyright (c) 2026 Flare community contributors
# SPDX-License-Identifier: Apache-2.0

"""Pinned Flare 5a4e867 MTP byte-equality test with keyword forwarding.

The upstream capture wrapper predates allocate/scale_scratch keyword arguments.
Forward those unchanged; retain the original snapshot checks and assertions.
"""

import os
from pathlib import Path

import pytest
import torch
from safetensors import safe_open

from ignition.components.parallel import TensorParallelShard
from ignition.preparation.checkpoint import inspect_indexed_checkpoint
from ignition.recipes.glm53.weights import TEXT_PREFIX, GlmWeightLoader


@pytest.fixture(scope="module")
def manifest():
    snapshot = Path(os.environ.get("FLARE_GLM53_SNAPSHOT",
        "/data/checkpoint-releases/GLM-5.3-Flash-NVFP4-MXFP8-CSF-QAD"))
    if not snapshot.is_dir():
        pytest.skip("GLM 5.3 Flash checkpoint is not available")
    return inspect_indexed_checkpoint(snapshot)


def read(manifest, name, extent=None):
    with safe_open(str(manifest.snapshot / manifest.tensors[name].shard), framework="pt") as source:
        if extent is not None:
            return source.get_slice(name)[extent].clone()
        return source.get_tensor(name).clone()


cuda = pytest.mark.skipif(os.environ.get("FLARE_RUN_CUDA_TESTS") != "1",
                         reason="requires FLARE_RUN_CUDA_TESTS=1 and an assigned GPU")


@cuda
@pytest.mark.parametrize("world,rank", [(2, 1), (4, 3)])
def test_mtp_experts_preserve_packed_weights_and_e4m3_scales(manifest, world, rank, monkeypatch):
    from b12x._lib.intrinsics.reference import swizzle_block_scale
    from b12x.moe import fused_moe

    packed = {}
    prepare = fused_moe.prepare_weights

    def capture(*, plan, weights, **kwargs):
        for name in ("w13", "w2", "w13_block_scales", "w2_block_scales"):
            packed[name] = getattr(weights, name).clone()
        return prepare(plan=plan, weights=weights, **kwargs)

    monkeypatch.setattr(fused_moe, "prepare_weights", capture)

    assert os.environ.get("CUDA_VISIBLE_DEVICES"), "assign a CUDA device explicitly"
    shard = TensorParallelShard(rank, world)
    ids = (0, 287)
    prefix = f"{TEXT_PREFIX}.layers.45.mlp.experts"
    with GlmWeightLoader(manifest, "cuda:0", shard=shard,
                         prefixes=tuple(f"{prefix}.{i}." for i in ids)) as loader:
        experts = loader.load_experts(45, expert_ids=ids)
        assert loader._session.torch_copy_bytes == 0
    assert experts.plan.activation.mode == "a16"
    first, last = shard.partition(2048)
    weights, scales = {}, {}
    for projection in ("up_proj", "gate_proj", "down_proj"):
        extent = (slice(None), slice(first // 2, last // 2)) if projection == "down_proj" else slice(first, last)
        scale_extent = (slice(None), slice(first // 16, last // 16)) if projection == "down_proj" else slice(first, last)
        weights[projection] = torch.stack([read(manifest, f"{prefix}.{expert}.{projection}.weight", extent) for expert in ids])
        scales[projection] = torch.stack([read(manifest, f"{prefix}.{expert}.{projection}.weight_scale", scale_extent) for expert in ids])
    assert torch.equal(packed["w13"].cpu(), torch.cat((weights["up_proj"], weights["gate_proj"]), dim=1))
    assert torch.equal(packed["w2"].cpu(), weights["down_proj"])
    for actual, expected in ((packed["w13_block_scales"], torch.cat((scales["up_proj"], scales["gate_proj"]), dim=1)),
                             (packed["w2_block_scales"], scales["down_proj"])):
        expected = swizzle_block_scale(expected.cuda())
        assert torch.equal(actual.view(torch.uint8), expected.view(torch.uint8))
