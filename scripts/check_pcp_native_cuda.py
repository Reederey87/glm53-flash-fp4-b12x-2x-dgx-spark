"""Policy snapshots around the unchanged native/pinned compound probe."""
import hashlib
import argparse
import json
import os
import re
from pathlib import Path
import sys
import time
from pcp_bound_snapshot import validate as validate_policy
from kernel_memory_counters import snapshot

PARENT_SHA='3c3b1d13ec9800c868f6fb17174ad2debebfc422be20dd367b442809c56218dc'
EXPECTED_STATE=dict(torch_git='cf30153c4c131c8164ee7798e5022d810682e2cb',device_index=0,
    backend='native',effective_settings='',optimize=0)


def allocator_state(torch):
    state=dict(torch_git=torch.version.git_version,device_index=torch.cuda.current_device(),
        backend=torch.cuda.memory.get_allocator_backend(),effective_settings=torch._C._accelerator_getAllocatorSettings(),optimize=sys.flags.optimize)
    if state!=EXPECTED_STATE:raise ValueError('source/device/effective backend differs')
    return state


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--device-spelling',choices=('indexed','unindexed'),required=True)
    parser.add_argument('--node',choices=('head','worker'),required=True);parser.add_argument('--run-id',required=True);args=parser.parse_args()
    if not re.fullmatch('[0-9a-f]{32}',args.run_id):raise ValueError('invalid invocation identity')
    if sys.flags.optimize or any(os.environ.get(k) for k in ('PYTORCH_CUDA_ALLOC_CONF','PYTORCH_ALLOC_CONF','PYTORCH_HIP_ALLOC_CONF')):
        raise ValueError('default backend/assertions required')
    if hashlib.sha256(Path(__file__).with_name('check_native_ownership_cuda.py').read_bytes()).hexdigest()!=PARENT_SHA:
        raise ValueError('compound parent changed')
    import check_native_ownership_cuda as parent
    torch=parent.torch;torch.cuda.init()
    state=allocator_state(torch)
    before=validate_policy(snapshot(512),512);begin=time.time_ns()
    print('B12X_PCP_NATIVE_BEGIN '+json.dumps(dict(pid=os.getpid(),utc_ns=begin,kernel=before,
        node=args.node,run_id=args.run_id,device_spelling=args.device_spelling,parent_sha256=PARENT_SHA,allocator_state=state,
        scope='model-free-entry-not-model-profile'),separators=(',',':')),flush=True)
    sys.argv=[sys.argv[0],'--device-spelling',args.device_spelling]
    parent.main()
    state=allocator_state(torch)
    after=validate_policy(snapshot(512),512)
    print('B12X_PCP_NATIVE_END '+json.dumps(dict(pid=os.getpid(),utc_ns=time.time_ns(),kernel=after,
        node=args.node,run_id=args.run_id,device_spelling=args.device_spelling,parent_sha256=PARENT_SHA,allocator_state=state,
        checkpoint_loaded=False,server_loaded=False,checkpoint_deployment_cleared=False),separators=(',',':')),flush=True)


if __name__=='__main__':main()
