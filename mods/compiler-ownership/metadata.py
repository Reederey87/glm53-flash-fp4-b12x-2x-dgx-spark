"""Bounded debugging aggregates; never mutate compiler owners or read tensors."""
from collections import Counter
import gc
import re
import sys

TARGETS = frozenset((
    'torch._inductor.output_code.CompiledFxGraph',
    'torch._inductor.runtime.triton_heuristics.CachingAutotuner',
    'torch._inductor.triton_bundler.TritonBundle',
    'torch._inductor.triton_bundler.TritonKernelArtifacts',
    'torch._inductor.triton_bundler.TritonKernelArtifact',
    'triton.compiler.compiler.CompiledKernel',
    'vllm.compilation.caching.StandaloneCompiledArtifacts',
    'vllm.compilation.caching.VllmSerializableFunction',
))
SKIP = frozenset(('constants', 'torchbind_constants', 'example_inputs', 'graph_module',
                  '_original_gm', 'current_callable', 'optimized_call', 'fn', 'runtime_env'))


def qualified(value):
    kind = type(value)
    module = type.__getattribute__(kind, '__module__')
    name = type.__getattribute__(kind, '__name__')
    return module + '.' + name if type(module) is str and type(name) is str else ''


def compiler_summary(objects=None, *, max_nodes=100000, max_depth=6, max_gc_objects=2000000):
    objects = gc.get_objects() if objects is None else objects
    counts = Counter(); payloads = Counter(); unique = set(); seen = set()
    visited = 0; depth_omissions = 0; truncated = False; uninspectable = 0

    def walk(value, owner, depth):
        nonlocal visited, depth_omissions, truncated, uninspectable
        if id(value) in seen:
            return
        if visited >= max_nodes:
            truncated = True
            return
        seen.add(id(value)); visited += 1
        kind = type(value)
        if kind in (str, bytes, bytearray):
            # Builtin sizes only; no extension __sizeof__, repr or source dump.
            if id(value) not in unique:
                unique.add(id(value)); payloads[owner] += sys.getsizeof(value)
            return
        if depth >= max_depth:
            depth_omissions += 1
            return
        if kind is dict:
            children = value.values()
        elif kind in (list, tuple):
            children = value
        elif qualified(value) in TARGETS:
            try: state = object.__getattribute__(value, '__dict__')
            except AttributeError:
                uninspectable += 1; return
            children = (v for k, v in state.items() if k not in SKIP)
        else:
            return
        for child in children:
            walk(child, owner, depth+1)
            if truncated:
                break

    for index, value in enumerate(objects):
        if index >= max_gc_objects:
            truncated = True; break
        name = qualified(value)
        if name not in TARGETS:
            continue
        counts[name] += 1
        try: state = object.__getattribute__(value, '__dict__')
        except AttributeError:
            uninspectable += 1; continue
        for field, child in state.items():
            if type(field) is str and field not in SKIP:
                walk(child, name.rsplit('.', 1)[1]+'.'+field[:64], 0)
    return dict(scanned_objects=min(len(objects),max_gc_objects), gc_objects_total=len(objects),
                max_gc_objects=max_gc_objects, target_counts=dict(counts),
                unique_payload_bytes=sum(payloads.values()), unique_payload_objects=len(unique),
                largest_fields=payloads.most_common(12), visited_metadata_nodes=visited,
                uninspectable_targets=uninspectable,
                depth_omissions=depth_omissions, truncated=truncated,
                max_nodes=max_nodes, max_depth=max_depth, coverage='GC-tracked known types; bounded metadata only')


def mapping_summary(source, *, max_maps=16384):
    metrics = ('Rss', 'Pss', 'Anonymous', 'Private_Dirty', 'Locked')
    totals = {}; bucket = None; count = 0; truncated = False
    header = re.compile(r'^[0-9a-f]+-[0-9a-f]+ ')
    for line in source:
        if header.match(line):
            count += 1
            if count > max_maps:
                truncated = True; break
            parts = line.split(None, 5)
            label = parts[5].strip() if len(parts) == 6 else ''
            if label == '[heap]': bucket = 'heap'
            elif not label or label.startswith('[anon'): bucket = 'anonymous'
            elif label.startswith('[stack'): bucket = 'stack'
            elif label.startswith('['): bucket = 'special'
            else: bucket = 'file'
            totals.setdefault(bucket, dict(maps=0, **{key:0 for key in metrics}))['maps'] += 1
        elif bucket is not None:
            key, _, value = line.partition(':')
            if key in metrics:
                totals[bucket][key] += int(value.split()[0]) * 1024
    return dict(buckets=totals, maps=min(count, max_maps), truncated=truncated, max_maps=max_maps)
