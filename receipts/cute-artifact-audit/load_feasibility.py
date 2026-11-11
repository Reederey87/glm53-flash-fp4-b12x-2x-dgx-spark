"""Model-free host AOT loading feasibility; no GPU access or kernel execution.

Private staging only. Does not qualify graph correctness or physical savings.
Run object/shared modes in separate fresh processes with the same inventory.
"""
import argparse
import hashlib
import inspect
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def memory():
    selected = {'Rss', 'Pss', 'Pss_Anon', 'Pss_File', 'Anonymous', 'Swap'}
    result = {}
    for line in Path('/proc/self/smaps_rollup').read_text().splitlines():
        field, _, rest = line.partition(':')
        if field in selected:
            result[field] = int(rest.split()[0]) * 1024
    for line in Path('/proc/meminfo').read_text().splitlines():
        if line.startswith('MemAvailable:'):
            result['MemAvailable'] = int(line.split()[1]) * 1024
    return result


def digest(path):
    with Path(path).open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inventory', type=Path)
    parser.add_argument('root', type=Path)
    parser.add_argument('--mode', choices=('object', 'shared'), required=True)
    parser.add_argument('--count', type=int, default=32)
    args = parser.parse_args()
    if os.environ.get('CUDA_VISIBLE_DEVICES') != '':
        raise ValueError('requires CUDA_VISIBLE_DEVICES empty; host-only feasibility')
    if any(Path('/dev').glob('nvidia*')) or any(Path('/dev').glob('nvhost*')) or any(Path('/dev/dri').glob('render*')):
        raise ValueError('GPU device nodes must be absent')
    if not os.statvfs(args.root).f_flag & os.ST_RDONLY:
        raise ValueError('canonical cache must be mounted read-only')
    if not 1 <= args.count <= 64:
        raise ValueError('count outside feasibility bound')
    audit = json.loads(args.inventory.read_text())
    if audit.get('version') != 2 or not audit.get('scan_complete'):
        raise ValueError('requires completed v2 artifact audit')
    rows = sorted(audit['artifacts'], key=lambda row: (-row['object_bytes'], row['key']))[:args.count]
    if len(rows) != args.count:
        raise ValueError('not enough artifacts')
    import cutlass.cute
    from cutlass.base_dsl.export.external_binary_module import ExternalBinaryModule
    provider = ExternalBinaryModule.load_provider
    libraries = provider.dsl._get_dsl().get_shared_libs()
    provenance = {'inventory_sha256': digest(args.inventory),
                  'provider_sha256': digest(inspect.getfile(ExternalBinaryModule)),
                  'libraries': {name: digest(name) for name in libraries},
                  'compiler_version': subprocess.run(['g++', '--version'], check=True,
                      capture_output=True, text=True, timeout=10).stdout[:4096]}
    modules, functions, checkpoints = [], [], []
    generated = {}
    with tempfile.TemporaryDirectory(prefix='b12x-host-load-') as directory:
        stage = Path(directory)
        for row in rows:
            source = args.root / row['key'][:2] / (row['key'] + '.o')
            destination = stage / source.name
            shutil.copyfile(source, destination)
            with destination.open('rb') as file:
                if hashlib.file_digest(file, 'sha256').hexdigest() != row['object_sha256']:
                    raise ValueError('staged object differs from audited source')
            # Both arms prepare identical files before baseline. Initializers may
            # execute during loading; no CUDA devices are exposed to either arm.
            subprocess.run(['g++', '-shared', '-Wl,-z,defs', '-o', str(destination.with_suffix('.so')),
                            str(destination), *libraries], check=True, capture_output=True, timeout=30)
            generated[row['key']] = digest(destination.with_suffix('.so'))
        baseline = memory()
        for number, row in enumerate(rows, 1):
            artifact = stage / (row['key'] + ('.o' if args.mode == 'object' else '.so'))
            module = ExternalBinaryModule(str(artifact))
            function = getattr(module, 'b12x_cute_' + row['key'])
            state = vars(function)
            if (state['engine'] is not module.engine or state['ir_module'] is not None
                    or state['artifacts'] is not None or not state['load_from_binary']
                    or state['jit_module'] is not None or state['_default_executor'] is not None):
                raise ValueError('unexpected binary-function state or initialized executor')
            modules.append(module); functions.append(function)
            if number in {1, 2, 4, 8, 16, 32, 64} or number == args.count:
                checkpoints.append({'loaded': number, 'memory': memory()})
        print(json.dumps({'mode': args.mode, 'scope': 'host-only-no-GPU-no-execution',
                          'keys': [row['key'] for row in rows], 'runtime_libraries': libraries,
                          'provenance': provenance, 'generated_shared_sha256': generated,
                          'baseline': baseline, 'checkpoints': checkpoints,
                          'engine_wrappers': len({id(module.engine) for module in modules}),
                          'strong_modules': len(modules), 'strong_functions': len(functions),
                          'requires_readonly_canonical_mount': True}, sort_keys=True))


if __name__ == '__main__':
    main()
