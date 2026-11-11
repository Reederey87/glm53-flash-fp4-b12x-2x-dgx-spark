"""Validate actual startup allocator activation AND restoration before smoke."""
import argparse
import json
import math
from pathlib import Path

MARKER='B12X_STARTUP_BOUND '


def validate(log, loader_hash, helper_hash, expected_pid, trace=None):
    records=[json.loads(line.split(MARKER,1)[1]) for line in log.splitlines() if MARKER in line]
    if len(records)<4 or len(records)%2:
        raise ValueError('need complete target and MTP bound scopes')
    for index in range(0,len(records),2):
        entered,exited=records[index:index+2]
        for record in (entered,exited):
            if record['loader_sha256']!=loader_hash or record['bound_sha256']!=helper_hash:
                raise ValueError('incorrect bound installation hashes')
            if record['pid']!=expected_pid or record['scope']!=index//2+1:
                raise ValueError('mixed worker or missing/reordered bound scope')
            if record['backend']!='native':
                raise ValueError('bound did not use native allocator')
            if record['previous']!=1.0 or record['requested']!=.8:
                raise ValueError('unexpected startup allocator controls')
            if type(record['capacity']) is not int or record['capacity']<=0 or record['limit']!=int(.8*record['capacity']):
                raise ValueError('incorrect allocator capacity/limit')
            if record['reserved']<record['allocated'] or record['reserved']>record['limit']:
                raise ValueError('allocator reservation outside startup cap')
        if entered['event']!='enter' or exited['event']!='exit' or exited['success'] is not True:
            raise ValueError('incomplete or failed postload scope')
        if entered['fraction']!=.8 or exited['fraction']!=1.0:
            raise ValueError('allocator cap did not activate/restore')
    if trace is not None:
        if trace['minimum_available']<4*1024**3:
            raise ValueError('startup did not retain pre-registered 4 GiB headroom')
        if trace['maximum_reserved']>min(r['limit'] for r in records):
            raise ValueError('postload trace exceeded allocator cap')
        starts=[r for r in trace['records'] if r['phase']=='postload-enter']
        ends=[r for r in trace['records'] if r['phase']=='postload-exit']
        if len(starts)!=len(records)//2 or len(ends)!=len(starts):
            raise ValueError('postload trace and bound scopes differ')
        for scope,(start,end) in enumerate(zip(starts,ends)):
            entered,exited=records[2*scope:2*scope+2]
            if not entered['utc_ns']<=start['utc_ns']<=end['utc_ns']<=exited['utc_ns']:
                raise ValueError('bound did not enclose postload trace')
    return dict(scopes=len(records)//2,pid=expected_pid,records=records,restored_fraction=1.0)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('log',type=Path)
    parser.add_argument('--loader',required=True)
    parser.add_argument('--helper',required=True)
    parser.add_argument('--trace',required=True,type=Path)
    args=parser.parse_args()
    trace=json.loads(args.trace.read_text())
    print(json.dumps(validate(args.log.read_text(),args.loader,args.helper,trace['pid'],trace),indent=2))
