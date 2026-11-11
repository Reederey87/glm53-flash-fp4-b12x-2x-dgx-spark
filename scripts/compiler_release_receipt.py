"""Verify actual lookup eviction, retained identity and native RSS reclamation."""
import argparse
import json
from pathlib import Path

MARKER='B12X_COMPILER_RELEASE '
COMPILER_SHA='3a73fe9d56fe1bf6277b92f8ec7c28b9b0a7b6c02e1ca2c04106c9922e83694b'
PLAN_SHA='272ddb4f674b437e185e6c52274d87333534e0100db29ff5cf88a2e2fefc3e24'


def validate(log,worker,helper,pid,minimum=1024**3):
    rows=[json.loads(line.split(MARKER,1)[1]) for line in log.splitlines() if MARKER in line]
    if len(rows)!=2 or [r['phase'] for r in rows]!=['before','after']:
        raise ValueError('need exactly one compiler lookup release')
    before,after=rows
    for row in rows:
        if row['version']!=1 or row['boundary']!='post-explicit-profile' or row['pid']!=pid or row['worker_sha256']!=worker or row['helper_sha256']!=helper:
            raise ValueError('wrong compiler-release installation/process')
        if row['compiler_sha256']!=COMPILER_SHA or row['plan_sha256']!=PLAN_SHA:
            raise ValueError('wrong native compiler/provider source')
        for key in ('allocated','reserved','pinned_owned','pinned_active','result','device_index','utc_ns','retained_program_owners'):
            if type(row[key]) is not int or row[key]<0:raise ValueError('invalid compiler release counter')
        if row['fraction']!=1.0 or row['allocated']>row['reserved'] or row['pinned_active']>row['pinned_owned'] or row['result']<=0:
            raise ValueError('invalid compiler release allocator state')
        if row['host']['MemAvailable']<4*1024**3:raise ValueError('compiler release crossed4GiB early headroom gate')
        for key in ('memory_cache_size','spec_memo_size'):
            if type(row['cache'][key]) is not int or row['cache'][key]<0:raise ValueError('invalid compiler cache count')
    for key in ('allocated','reserved','pinned_owned','pinned_active','fraction','device_index','result','retained_program_owners','retained_identity_sha256','compiler_provider'):
        if before[key]!=after[key]:raise ValueError('compiler eviction changed live ownership or admission')
    if before['cache']['memory_cache_size']+before['cache']['spec_memo_size']==0 or after['cache']['memory_cache_size'] or after['cache']['spec_memo_size']:
        raise ValueError('compiler lookup eviction not proven')
    if after['utc_ns']<before['utc_ns'] or after['trim_result'] not in (0,1) or type(after['elapsed_ns']) is not int or after['elapsed_ns']<0:
        raise ValueError('invalid compiler release ordering/duration')
    reclaimed=before['process']['RssAnon']-after['process']['RssAnon']
    if reclaimed<minimum:raise ValueError('compiler release below required reclamation')
    return dict(records=rows,reclaimed_anon_bytes=reclaimed,pid=pid,inference_qualified=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('log',type=Path)
    parser.add_argument('--worker',required=True);parser.add_argument('--helper',required=True)
    parser.add_argument('--trace',type=Path,required=True);parser.add_argument('--minimum',type=int,default=1024**3)
    args=parser.parse_args()
    print(json.dumps(validate(args.log.read_text(),args.worker,args.helper,json.loads(args.trace.read_text())['pid'],args.minimum),indent=2))
