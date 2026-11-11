"""Bounded stored-field inventory. Never load, execute, resolve or evict owners."""
from collections import Counter, deque
import hashlib
import json
from pathlib import Path
import re
import sys
import time
from types import FunctionType, ModuleType

PROVIDERS = {
    'b12x._lib.compile_plan': '272ddb4f674b437e185e6c52274d87333534e0100db29ff5cf88a2e2fefc3e24',
    'cutlass.base_dsl.jit_executor': '06c91ba84b7a1b43b93e0f2de97e872426104ba1773f904c58845d5ae74870ea',
    'cutlass.cutlass_dsl.cuda_jit_executor': '1589949f04c39184dc3ef9287720b029bb4f8e1161fb8e20a416977cb6bf6583',
    'triton.compiler.compiler': '021a45ca590052ab6ca6d850eb0a102abf542165836ad92bfb3bb573218fc5d3',
    'vllm.model_executor.warmup.b12x_prepare': '0b8717cc17a9dca6aa772af9aeb33a7bbb7769461aa8c63c00d2db2b18598112',
}
LIMITS = dict(roots=4096, nodes=8192, edges=32768, depth=16,
              output_bytes=1024**2, seconds=2)
PLAN_CLASSES = ('_RetainedPrograms', 'ProgramKey', 'ProgramBundle',
                'CompiledCuTeProgram', 'DeferredCuTeKernel', 'DeferredTritonKernel')
BASE_CLASSES = ('JitCompiledFunction', 'JitExecutor', 'JitModule', 'JitFunctionArtifacts')


def stored(value):
    # Call only after exact-class allowlisting; no forwarded getattr/properties.
    data = object.__getattribute__(value, '__dict__')
    if type(data) is not dict:
        raise ValueError('expected stored instance dictionary')
    return data


def providers():
    modules = {}
    for name, expected in PROVIDERS.items():
        module = sys.modules.get(name)
        if type(module) is not ModuleType:
            raise ValueError('required provider is not already loaded: ' + name)
        data = module.__dict__
        path = Path(data['__file__'])
        if path.stat().st_size > 256 * 1024 or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('provider source mismatch: ' + name)
        modules[name] = data
    plan = modules['b12x._lib.compile_plan']
    classes = {plan[name]: name for name in PLAN_CLASSES}
    base = modules['cutlass.base_dsl.jit_executor']
    classes.update({base[name]: name for name in BASE_CLASSES})
    cuda = modules['cutlass.cutlass_dsl.cuda_jit_executor']
    classes.update({cuda[name]: name for name in ('CudaDialectJitCompiledFunction', 'CudaDialectJitModule')})
    classes[modules['triton.compiler.compiler']['CompiledKernel']] = 'CompiledKernel'
    classes[FunctionType] = 'function'
    return plan, classes


def inactive(plan):
    if (plan['_RETAINED_PROGRAMS'].get() is not None or plan['_PLANNING'].get() is not None
            or type(plan['_OBSERVERS'].get()) is not tuple or plan['_OBSERVERS'].get()
            or plan['_COMPILE_ONLY_LAUNCHES'].get() is not False):
        raise ValueError('program materialization context still active')


def roots(plan, classes, limits):
    """Keep bounded temporary strong references; no weak registry is an owner."""
    result, identities, edges = [], [], 0
    for scope in plan['_LIVE_RETAINED_PROGRAMS']:
        if len(result) >= limits['roots'] or classes.get(type(scope)) != '_RetainedPrograms':
            raise ValueError('unknown or excessive retention scopes')
        data = stored(scope)
        owners, cache = data['owners'], data['cache']
        if type(owners) is not dict or type(cache) is not dict:
            raise ValueError('unexpected scoped ownership containers')
        edges += len(owners) + len(cache)
        if edges > limits['edges']:
            raise ValueError('root edge limit exceeded')
        own = []
        for key, value in owners.items():
            if type(key) is not int or key != id(value):
                raise ValueError('invalid explicit owner identity')
            own.append(value)
        cached = list(cache.values())
        result.append((scope, own, cached))
        identities.append((id(scope), tuple(sorted(id(x) for x in own)),
                           tuple(sorted((id(k), id(v)) for k, v in cache.items()))))
    fingerprint = hashlib.sha256(json.dumps(sorted(identities), separators=(',', ':')).encode()).hexdigest()
    return result, fingerprint


def collect(plan, classes, limits=None):
    limits = dict(LIMITS if limits is None else limits)
    inactive(plan)
    scopes, before = roots(plan, classes, limits)
    nodes, edges, objects, known, pending = [], [], [], {}, deque()
    counts, programs, blobs, problems = Counter(), set(), set(), []
    charged = 0
    key_references = 0
    deadline = time.monotonic() + limits['seconds']

    def append(destination, value):
        nonlocal charged
        charged += len(json.dumps(value, separators=(',', ':')).encode()) + 2
        if charged > limits['output_bytes'] or time.monotonic() > deadline:
            raise ValueError('serialization/time limit exceeded')
        destination.append(value)

    def add(value, depth, opaque=None):
        if value is None:
            return None
        if id(value) in known:
            return known[id(value)]
        if len(nodes) >= limits['nodes'] or depth > limits['depth']:
            raise ValueError('node/depth limit exceeded')
        kind = opaque or classes.get(type(value), 'UNKNOWN')
        number = len(nodes)
        known[id(value)] = number; objects.append(value)
        node = dict(id=number, kind=kind)
        append(nodes, node); counts[kind] += 1
        if kind == 'UNKNOWN':
            problems.append('unknown carrier type')
        elif opaque is None:
            pending.append((number, value, depth))
        return number

    def edge(parent, label, value, depth, opaque=None):
        if len(edges) >= limits['edges']:
            raise ValueError('edge limit exceeded')
        child = add(value, depth + 1, opaque)
        if child is not None:
            append(edges, dict(parent=parent, field=label, child=child))

    def keys(node, values):
        nonlocal key_references
        if type(values) is not tuple or len(values) > limits['edges']:
            raise ValueError('invalid/bounded program tuple')
        recorded = []
        for program in values:
            key_references += 1
            if key_references > limits['edges']:
                raise ValueError('program reference limit exceeded')
            if classes.get(type(program)) != 'ProgramKey':
                raise ValueError('unknown program key')
            data = stored(program); dialect, key = data['dialect'], data['key']
            if dialect not in ('cute', 'triton') or type(key) is not str or not re.fullmatch('[0-9a-f]{64}', key):
                raise ValueError('invalid canonical program identity')
            pair = (dialect, key); programs.add(pair)
            recorded.append(dict(dialect=dialect, key=key))
        node['programs'] = recorded

    try:
        for scope, owners, cache in scopes:
            parent = add(scope, 0)
            for label, values in (('owners', owners), ('cache', cache)):
                for value in values:
                    edge(parent, label, value, 0)
        while pending:
            number, value, depth = pending.popleft()
            node = nodes[number]; kind = node['kind']; data = stored(value)
            if kind == '_RetainedPrograms':
                continue
            if kind in ('CompiledCuTeProgram', 'DeferredCuTeKernel', 'DeferredTritonKernel', 'function', 'ProgramBundle'):
                keys(node, data.get('programs' if kind == 'ProgramBundle' else '__b12x_programs__', ()))
                if kind == 'CompiledCuTeProgram':
                    edge(number, '_executable', data['_executable'], depth)
                elif kind.startswith('Deferred'):
                    node['unresolved'] = data['_resolved'] is None
                    edge(number, '_resolved', data['_resolved'], depth)
                elif kind == 'function':
                    dependencies = data.get('__b12x_dependencies__', ())
                    if type(dependencies) is not tuple or len(dependencies) > limits['edges']:
                        raise ValueError('invalid explicit dependencies')
                    if not dependencies and not node['programs']:
                        problems.append('unannotated function')
                    for child in dependencies:
                        edge(number, 'dependency', child, depth)
            elif kind in ('JitCompiledFunction', 'CudaDialectJitCompiledFunction'):
                for field in ('engine', 'jit_module', '_default_executor', 'artifacts'):
                    edge(number, field, data[field], depth, 'engine' if field == 'engine' else None)
                binary, prefix = data['load_from_binary'], data['prefix']
                if type(binary) is not bool or (prefix is not None and
                        (type(prefix) is not str or len(prefix) > 256)):
                    raise ValueError('invalid executable metadata')
                node.update(binary_loaded=binary, ir_present=data['ir_module'] is not None, prefix=prefix)
            elif kind == 'JitExecutor':
                edge(number, 'jit_module', data['jit_module'], depth)
            elif kind in ('JitModule', 'CudaDialectJitModule'):
                edge(number, 'engine', data['engine'], depth, 'engine')
                node['unloaded'] = data['_unloaded']
                libraries = data['cuda_library' if kind == 'CudaDialectJitModule' else 'cuda_modules']
                if type(libraries) is not list or type(node['unloaded']) is not bool:
                    raise ValueError('invalid materialized module fields')
                node['library_entries'] = len(libraries)
            elif kind == 'JitFunctionArtifacts':
                for field in ('PTX', 'CUBIN', 'SASS', 'MLIR'):
                    blob = data[field]
                    if blob is None:
                        continue
                    if type(blob) not in (str, bytes):
                        raise ValueError('unknown compiler payload type')
                    node[field + '_length'] = len(blob)
                    if id(blob) not in blobs:
                        blobs.add(id(blob)); counts['unique_payload_bytes' if type(blob) is bytes else 'unique_payload_characters'] += len(blob)
            elif kind == 'CompiledKernel':
                key = data['hash']
                if type(key) is not str or not re.fullmatch('[0-9a-f]{64}', key):
                    raise ValueError('invalid Triton program hash')
                programs.add(('triton', key)); node['programs'] = [dict(dialect='triton', key=key)]
            elif kind == 'ProgramKey':
                keys(node, (value,))
            else:
                problems.append('unhandled known carrier')
            # Charge filled metadata as well as the original skeletal row.
            charged += len(json.dumps(node, separators=(',', ':')).encode())
            if charged > limits['output_bytes'] or time.monotonic() > deadline:
                raise ValueError('filled metadata/time limit exceeded')
        inactive(plan)
        _, after = roots(plan, classes, limits)
        if before != after:
            raise ValueError('retention roots changed during inventory')
    except (ValueError, KeyError, RuntimeError) as error:
        problems.append(str(error)[:160])
    report = dict(version=1, complete=not problems, problems=problems[:16], limits=limits,
                  root_identity_sha256=before, counts=dict(counts), nodes=nodes, edges=edges,
                  programs=[dict(dialect=d, key=k) for d, k in sorted(programs)],
                  scope='selected-strong-scopes-and-explicit-dependencies',
                  engine_identity_is_native_bytes=False)
    if len(json.dumps(report, separators=(',', ':')).encode()) > limits['output_bytes']:
        raise ValueError('final inventory exceeds output bound')
    return report
