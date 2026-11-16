"""Independent checkpoint arithmetic for the served MXFP8/A16 vocabulary head.

Reference operands come directly from safetensors, not the prepared projection.
The scale-layout inverse is used only for a separate byte-preservation assertion.
"""
import os
from pathlib import Path

import torch
import torch.distributed as dist
from safetensors import safe_open


@torch.no_grad()
def load_checkpoint_head(rank, world, device):
    from b12x.gemm._shared.wo_mxfp8 import materialize_mxfp8_scale_rows
    from ignition.components.parallel import TensorParallelShard
    from ignition.preparation.checkpoint import inspect_indexed_checkpoint
    from ignition.recipes.glm53.weights import GlmWeightLoader

    manifest = inspect_indexed_checkpoint(Path(os.environ['FLARE_GLM53_SNAPSHOT']))
    shard = TensorParallelShard(rank, world)
    first, last = shard.partition(154880, alignment=64)
    raw = {}
    for name in ('lm_head.weight', 'lm_head.weight_scale'):
        with safe_open(str(manifest.snapshot / manifest.tensors[name].shard), framework='pt') as f:
            raw[name] = f.get_slice(name)[first:last].clone()
    values, scales = raw['lm_head.weight'], raw['lm_head.weight_scale']
    assert values.shape == (77440, 4096) and values.dtype == torch.float8_e4m3fn
    assert scales.shape == (77440, 128) and scales.dtype == torch.uint8
    assert not (scales == 255).any(), 'UE8M0 NaN scale in checkpoint head'
    assert torch.isfinite(values.float()).all()
    with GlmWeightLoader(manifest, device, shard=shard, prefixes=('lm_head.',)) as loader:
        weight = loader.load_linear('lm_head', rows=(first, last))
        assert loader._session.torch_copy_bytes == 0
    assert torch.equal(weight.weight.values.cpu().view(torch.uint8), values.view(torch.uint8))
    compact = materialize_mxfp8_scale_rows(weight.weight).reshape(77440, 128)
    assert torch.equal(compact.cpu().view(torch.uint8), scales)
    # Decode directly from original checkpoint bytes. No serving quantizer or GEMM
    # participates in this FP64 oracle, and no activation requantization is applied.
    reference = values.to(device=device, dtype=torch.float64).reshape(77440, 128, 32)
    reference.mul_(torch.exp2(scales.to(device=device, dtype=torch.float64) - 127).unsqueeze(-1))
    assert torch.isfinite(reference).all()
    return weight, reference.reshape(77440, 4096)


@torch.no_grad()
def checkpoint_reference(source, weight, group, world, output_dtype):
    local = (source.double() @ weight.T).to(output_dtype).cpu()
    shards = [None] * world
    dist.all_gather_object(shards, local, group=group)
    assert all(x.shape == local.shape and torch.isfinite(x).all() for x in shards)
    return torch.cat(shards, dim=1).to(source.device)
