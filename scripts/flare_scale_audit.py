"""Audit full-layer GLM CSF scale populations against the packed A16 boundary.

Uses the pinned independent CPU checkpoint decoder. This is a storage/scale
audit, not CUDA replay or a full-model numerical qualification. Run on an idle
head in the pinned Flare preparation environment, with timed restoration armed.
"""
import argparse
from collections import Counter
import fcntl
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import socket

FLARE_REVISION = '5a4e867954593b2e05bba43bc2a6eeaddca402d7'
CHECKPOINT_REVISION = '76348ddb2be2e35e39ecfc00e75dc07703f4f3d5'
PREFIX = 'model.language_model.layers'


def e4m3(code):
    if type(code) is not int or not 0 <= code <= 255:
        raise ValueError('invalid E4M3 byte')
    exponent, mantissa = (code >> 3) & 15, code & 7
    if exponent == 15 and mantissa == 7:
        raise ValueError('nonfinite scale')
    value = mantissa / 512 if exponent == 0 else (1 + mantissa / 8) * 2 ** (exponent - 7)
    if code & 128 and value:
        raise ValueError('negative block scale')
    return value


def scale_boundary(histogram):
    if len(histogram) != 256 or any(type(n) is not int or n < 0 for n in histogram) or not sum(histogram):
        raise ValueError('expected a populated 256-byte histogram')
    values = {code: e4m3(code) for code, count in enumerate(histogram) if count}
    maximum = max(values.values())
    factor = 2 ** math.floor(math.log2(448 / maximum)) if 0 < maximum < 448 else 1
    discarded = {str(code): histogram[code] for code, value in values.items() if 0 < value * factor < 1 / 64}
    return {'scale_count': sum(histogram), 'zero_scale_count': sum(histogram[c] for c, v in values.items() if v == 0),
            'maximum_scale': maximum, 'full_layer_lifting_factor': factor,
            'nonzero_scales_below_packed_boundary': sum(discarded.values()), 'below_boundary_byte_counts': discarded,
            'histogram': histogram}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upstream', type=Path, required=True)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--layers', required=True, help='Explicit target layers, e.g. 3,24,44; all covers 3..44')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if socket.gethostname() != 'spark-a183':
        parser.error('run this qualification on the cluster head')
    lock = Path('/home/nvidia/b12x-flare/local/gpu-operation.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    layers = list(range(3, 45)) if args.layers == 'all' else [int(x) for x in args.layers.split(',')]
    if not layers or len(set(layers)) != len(layers) or any(not 3 <= x <= 44 for x in layers):
        parser.error('select distinct target routed-expert layers 3..44')
    if args.snapshot.name != CHECKPOINT_REVISION:
        parser.error('expected the pinned checkpoint snapshot')
    revision = subprocess.check_output(['git', '-C', str(args.upstream), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != FLARE_REVISION:
        raise ValueError('upstream revision differs from the audited decoder')
    if subprocess.check_output(['git', '-C', str(args.upstream), 'diff', '--name-only', 'HEAD'], text=True).strip():
        raise ValueError('upstream tracked sources are modified')
    # Refuse to compete with inference even though this audit does not use CUDA.
    running = subprocess.check_output(['systemctl', '--user', 'list-units', '--type=service',
                                      '--state=active,activating,deactivating', '--no-legend', '--plain'], text=True)
    for line in running.splitlines():
        unit = line.split()[0]
        if unit in ('vllm-b12x.service', 'b12x-flare@0.service', 'b12x-flare-prepare@0.service',
                    'b12x-flare-qualify@0.service', 'b12x-flare-build@0.service'):
            raise ValueError('GPU or incumbent unit is active: ' + unit)
    sys.path.insert(0, str(args.upstream))
    import torch
    from safetensors import safe_open
    from ignition.preparation.checkpoint import inspect_indexed_checkpoint
    from ignition.reference.qwen38_quant import decode_csf_scales, decode_csf_slab_scales

    torch.set_num_threads(2)
    if torch.cuda.is_initialized():
        raise ValueError('CPU audit unexpectedly initialized CUDA')
    manifest = inspect_indexed_checkpoint(args.snapshot)
    payload_bytes = 0
    payload_hash = hashlib.sha256()

    def read(name):
        nonlocal payload_bytes
        meta = manifest.tensors[name]
        with safe_open(str(args.snapshot / meta.shard), framework='pt', device='cpu') as source:
            view = source.get_slice(name)
            if tuple(view.get_shape()) != meta.shape or view.get_dtype() != meta.dtype:
                raise ValueError('scale tensor metadata changed after inspection')
            value = source.get_tensor(name).clone()
        payload_bytes += meta.nbytes
        payload_hash.update(json.dumps([name, meta.dtype, meta.shape, meta.nbytes], separators=(',', ':')).encode() + b'\n')
        payload_hash.update(value.view(torch.uint8).numpy().tobytes())
        return value

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x') as output:
        def emit(value):
            output.write(json.dumps(value, allow_nan=False) + '\n')
            output.flush()

        emit({'manifest': {'checkpoint_revision': CHECKPOINT_REVISION, 'flare_revision': revision,
                           'shard_headers_sha256': {shard.path: shard.header_sha256 for shard in manifest.shards},
                           'layers': layers, 'tp': 2,
                           'experts_per_layer': 288, 'activation_dtype': 'bfloat16',
                           'qualification': 'CPU scale population only; no packed-weight or native replay proof'}})
        affected = 0
        for layer in layers:
            histograms = {(rank, projection): Counter() for rank in (0, 1) for projection in ('w13', 'w2')}
            for expert in range(288):
                for projection in ('up_proj', 'gate_proj', 'down_proj'):
                    name = f'{PREFIX}.{layer}.mlp.experts.{expert}.{projection}.weight_scale'
                    rows, columns = (4096, 128) if projection == 'down_proj' else (2048, 256)
                    if name + '.csf32_bases' in manifest.tensors:
                        scales = decode_csf_scales(*(read(name + '.csf32_' + suffix)
                                                    for suffix in ('bases', 'codes', 'page_bases', 'offsets', 'exceptions')),
                                                   rows=rows, columns=columns)
                    else:
                        scales = decode_csf_slab_scales(read(name + '.nvfp4_csf_fixed'),
                                                       read(name + '.nvfp4_csf_exceptions'), rows=rows, columns=columns)
                    for rank in (0, 1):
                        values = scales[:, rank * 64:(rank + 1) * 64] if projection == 'down_proj' else scales[rank * 1024:(rank + 1) * 1024]
                        counts = torch.bincount(values.reshape(-1).to(torch.int64), minlength=256).tolist()
                        target = histograms[rank, 'w2' if projection == 'down_proj' else 'w13']
                        target.update({code: count for code, count in enumerate(counts) if count})
                if (expert + 1) % 32 == 0:
                    print(json.dumps({'layer': layer, 'experts_scanned': expert + 1}), flush=True)
            for (rank, projection), histogram in histograms.items():
                result = scale_boundary([histogram[code] for code in range(256)])
                expected = 288 * (2 if projection == 'w13' else 1) * 262144
                if result['scale_count'] != expected:
                    raise ValueError('incomplete rank-local scale population')
                affected += result['nonzero_scales_below_packed_boundary']
                emit({'layer': layer, 'rank': rank, 'projection': projection, **result})
            if torch.cuda.is_initialized():
                raise ValueError('CPU audit unexpectedly initialized CUDA')
        emit({'complete': True, 'layers_scanned': len(layers), 'source_payload_bytes_read': payload_bytes,
              'scanned_scale_payloads_sha256': payload_hash.hexdigest(),
              'nonzero_scales_below_packed_boundary': affected,
              'scope': 'all target CSF layers' if layers == list(range(3, 45)) else 'selected target layers only',
              'cuda_initialized': False})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
