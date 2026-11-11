"""Verify the actual outer warmup release before correctness/speed measurement."""
import argparse
import json
from pathlib import Path

MARKER='B12X_WARMUP_CACHE '


def validate(log,worker_hash,helper_hash,pid,minimum_reclaim=0):
    rows=[json.loads(line.split(MARKER,1)[1]) for line in log.splitlines() if MARKER in line]
    if len(rows)!=2 or [r['phase'] for r in rows]!=['before','after']:
        raise ValueError('need exactly one complete outer-warmup cache return')
    before,after=rows
    for row in rows:
        if row['pid']!=pid or row['worker_sha256']!=worker_hash or row['helper_sha256']!=helper_hash:
            raise ValueError('wrong process or cache-return installation hashes')
        if row['fraction']!=1.0 or row['allocated']>row['reserved']:
            raise ValueError('incorrect allocator state at warmup return')
        if row['host']['MemAvailable']<2*1024**3:
            raise ValueError('warmup cache receipt crossed host floor')
    if before['device_index']!=after['device_index'] or after['allocated']!=before['allocated'] or after['reserved']>before['reserved'] or after['utc_ns']<before['utc_ns']:
        raise ValueError('cache return changed live storage or invalid ordering')
    returned=before['reserved']-after['reserved']
    if returned<minimum_reclaim:raise ValueError('cache return below pre-registered minimum')
    return dict(pid=pid,returned_bytes=returned,records=rows)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('log',type=Path)
    parser.add_argument('--worker',required=True);parser.add_argument('--helper',required=True)
    parser.add_argument('--trace',type=Path,required=True)
    parser.add_argument('--minimum-reclaim',type=int,default=0);args=parser.parse_args()
    print(json.dumps(validate(args.log.read_text(),args.worker,args.helper,json.loads(args.trace.read_text())['pid'],args.minimum_reclaim),indent=2))
