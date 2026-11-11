"""Validate the source/PID-bound terminal native inventory and common proofs."""
import argparse
import base64
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re

from host_ownership_receipt import validate as validate_memory
from pinned_cache_receipt import validate as validate_pinned

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('native_metadata_constants', ROOT/'mods/native-ownership/metadata.py')
metadata = importlib.util.module_from_spec(spec); spec.loader.exec_module(metadata)
PROVIDERS, LIMITS = metadata.PROVIDERS, metadata.LIMITS
PINNED_SHA = '1761e9aeb863da2cb307fc7094c30af495aa78ff9e135e9d58d81df7b6c82ac6'
BOUNDARY = 'post-profile-pinned-before-KV'
MARKER = 'B12X_NATIVE_OWNERS '


def natural(value):
    return type(value) is int and value >= 0


def validate(log, worker, helper, collector, trace, boundary=BOUNDARY):
    proof = validate_memory(log, worker, helper, trace['pid'], boundary)
    row = proof['record']
    if (row['metadata_sha256'] != collector or row['providers'] != PROVIDERS
            or row['pinned_helper_sha256'] != PINNED_SHA or row['profile_completed'] is not True
            or row['inventory_complete'] is not True or row['process_coverage'] != 'self-parent'
            or row['host']['MemAvailable'] < 10*1024**3
            or type(row['result']) is not int or not 0 < row['result'] <= 17*1024**3):
        raise ValueError('native inventory provider/state/admission mismatch')
    pinned = validate_pinned(log, worker, PINNED_SHA, trace)
    before = row['before']
    for snap in (before,row):
        if (type(snap['fraction']) not in (int,float) or snap['fraction']!=1
                or type(snap['gc_enabled']) is not bool or not natural(snap['frozen_objects'])
                or not all(natural(snap[k]) for k in ('allocated','reserved','device_index','utc_ns'))):
            raise ValueError('invalid native snapshot types')
    if (before['pid'] != row['pid'] or before['ppid'] != row['ppid'] or before['host']['MemAvailable'] < 10*1024**3
            or not pinned['records'][-1]['utc_ns'] <= before['utc_ns'] <= row['utc_ns']):
        raise ValueError('native inventory ordering/entry headroom mismatch')
    for key in ('allocated','reserved','fraction','pinned','gc_enabled','frozen_objects','device_index'):
        if before[key] != row[key]:
            raise ValueError('native inventory changed frozen live state')
    for snap in (before,row):
        if (set(p['pid'] for p in snap['processes']) != {row['pid'],row['ppid']}
                or len(snap['processes']) != len({row['pid'],row['ppid']})):
            raise ValueError('invalid self-parent process coverage')
        for p in snap['processes']:
            if not all(natural(p[k]) for k in ('VmRSS','RssAnon')) or not all(natural(v) for v in p['pss'].values()):
                raise ValueError('invalid process counters')
    own = lambda snap: next(p for p in snap['processes'] if p['pid']==row['pid'])
    if own(row)['RssAnon']-own(before)['RssAnon'] > 64*1024**2:
        raise ValueError('native inventory exceeded anonymous growth budget')
    chunks, main_position = [], None
    for position,line in enumerate(log.splitlines()):
        if 'B12X_HOST_OWNERSHIP ' in line:
            main_position = position
        if MARKER in line:
            if len(chunks) >= 512:
                raise ValueError('too many native inventory chunks')
            chunks.append((position,json.loads(line.split(MARKER,1)[1])))
    count = row['inventory_chunks']; sha = row['inventory_sha256']
    if type(count) is not int or not 0<count<=512 or len(chunks)!=count or not re.fullmatch('[0-9a-f]{64}',sha):
        raise ValueError('missing/invalid native inventory chunks')
    encoded = []
    for index,(position,chunk) in enumerate(chunks):
        if (position >= main_position or chunk['pid'] != row['pid'] or type(chunk['index']) is not int
                or chunk['index'] != index or chunk['count'] != count or chunk['sha256'] != sha
                or type(chunk['data']) is not str or not 0<len(chunk['data'])<=3000):
            raise ValueError('mixed/reordered native inventory chunks')
        encoded.append(chunk['data'])
    raw = base64.b64decode(''.join(encoded),validate=True)
    if len(raw)>LIMITS['output_bytes'] or hashlib.sha256(raw).hexdigest()!=sha:
        raise ValueError('native inventory size/digest mismatch')
    report = json.loads(raw)
    if (report['version'] != 1 or report['complete'] is not True or report['problems'] or report['limits'] != LIMITS
            or report['engine_identity_is_native_bytes'] is not False
            or report['scope'] != 'selected-strong-scopes-and-explicit-dependencies'
            or not re.fullmatch('[0-9a-f]{64}',report['root_identity_sha256'])):
        raise ValueError('incomplete/unbounded native inventory')
    nodes,edges=report['nodes'],report['edges']
    allowed=set(metadata.PLAN_CLASSES+metadata.BASE_CLASSES+('CudaDialectJitCompiledFunction','CudaDialectJitModule','CompiledKernel','function','engine'))
    if not 0<len(nodes)<=LIMITS['nodes'] or len(edges)>LIMITS['edges']:
        raise ValueError('native inventory graph size mismatch')
    for index,node in enumerate(nodes):
        if type(node['id']) is not int or node['id']!=index or node['kind'] not in allowed:
            raise ValueError('invalid native inventory node')
    for edge in edges:
        if (any(type(edge[k]) is not int or not 0<=edge[k]<len(nodes) for k in ('parent','child'))
                or edge['field'] not in ('owners','cache','_executable','_resolved','dependency','engine','jit_module','_default_executor','artifacts')):
            raise ValueError('invalid native inventory edge')
    counts=Counter(node['kind'] for node in nodes)
    if any(report['counts'].get(kind)!=number for kind,number in counts.items()):
        raise ValueError('native inventory count mismatch')
    if (not 0<counts['_RetainedPrograms']<=LIMITS['roots'] or not counts['CompiledCuTeProgram']
            or not counts['engine'] or not edges or len(report['programs'])>LIMITS['edges']):
        raise ValueError('no selected native ownership evidence')
    for p in report['programs']:
        if p['dialect'] not in ('cute','triton') or not re.fullmatch('[0-9a-f]{64}',p['key']):
            raise ValueError('invalid native inventory program identity')
    return dict(memory=proof,pinned_return=pinned,inventory=report,
                serving_qualified=False,native_bytes_attributed=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('log',type=Path)
    for name in ('worker','helper','metadata'):parser.add_argument('--'+name,required=True)
    parser.add_argument('--trace',type=Path,required=True);parser.add_argument('--boundary',default=BOUNDARY)
    args=parser.parse_args()
    print(json.dumps(validate(args.log.read_text(),args.worker,args.helper,args.metadata,
        json.loads(args.trace.read_text()),args.boundary),indent=2))
