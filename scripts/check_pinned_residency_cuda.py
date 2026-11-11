"""Matched fixture-only residency study. Measurement success is not qualification."""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import time
import types
import torch
from b12x.gemm import bf16_gemv
from b12x.preparation import PreparationSession,PreparedCall
import vllm.model_executor.warmup.b12x_prepare
from vllm.v1.worker.workspace import init_workspace_manager,current_workspace_manager,reset_workspace_manager


def fields(path,keys):
    out={}
    for line in Path(path).read_text().splitlines():
        key,_,rest=line.partition(':')
        if key in keys:out[key]=int(rest.split()[0])*1024
    if set(out)!=set(keys):raise RuntimeError('missing residency counters')
    return out


def sample(phase):
    stats=torch.cuda.memory.host_memory_stats()
    return dict(phase=phase,pid=os.getpid(),utc_ns=time.time_ns(),
        host=fields('/proc/meminfo',('MemFree','MemAvailable','AnonPages','Unevictable','Cached','Slab','SReclaimable')),
        process=fields('/proc/self/status',('RssAnon','VmRSS')),
        pss=fields('/proc/self/smaps_rollup',('Pss','Pss_Anon','Pss_File','Pss_Shmem')),
        pinned={k:stats[k] for k in ('allocated_bytes.current','active_bytes.current','num_host_alloc','num_host_free')},
        allocated=torch.cuda.memory_allocated(),reserved=torch.cuda.memory_reserved())


@torch.inference_mode()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--fixture',choices=('old','current'),required=True);args=parser.parse_args()
    helper=importlib.import_module('vllm.v1.worker._b12x_startup_pinned')
    helper_sha=hashlib.sha256(Path(helper.__file__).read_bytes()).hexdigest()
    if helper_sha!='1761e9aeb863da2cb307fc7094c30af495aa78ff9e135e9d58d81df7b6c82ac6':raise RuntimeError('wrong pinned helper')
    torch.cuda.init();torch.manual_seed(17);device=torch.device('cuda')
    init_workspace_manager(device)
    upload,=current_workspace_manager().get_simultaneous(((1024**2,),torch.uint8))
    source=torch.randn(2,2048,device=device,dtype=torch.bfloat16);weight=torch.randn(96,2048,device=device,dtype=torch.bfloat16)
    pinned=torch.ones(1024**2,dtype=torch.uint8,pin_memory=True)
    plan=bf16_gemv.plan(bf16_gemv.query_from_call(source,weight))
    request=plan.request(name='pinned-residency-study',prepare_call=lambda state:PreparedCall(run=lambda:state.run(source,weight)))
    graph=torch.cuda.CUDAGraph();host_graph=torch.cuda.CUDAGraph();rows=[]
    with PreparationSession(device=device,autotune=False,compile_workers=1) as session:
        session.prepare((request,))
        try:
            with session.capture(),torch.cuda.graph(graph):output=bf16_gemv.mm(source,weight,plan=plan)
            with torch.cuda.graph(host_graph):upload.copy_(pinned,non_blocking=True)
            torch.cuda.synchronize();rows.append(sample('before-fixture'))
            if rows[-1]['host']['MemAvailable']<10*1024**3:raise RuntimeError('study requires10GiB headroom')
            idle=[]
            if args.fixture=='old':
                staging=torch.empty(512*1024**2,dtype=torch.uint8,pin_memory=True);staging.fill_(37)
                rows.append(sample('resident-fixture'));del staging
                rows.append(sample('cached-before-profile-stub'))
            else:
                idle.append(torch.ones(512*1024**2,dtype=torch.uint8,pin_memory=True))
                rows.append(sample('resident-fixture'))
            worker=types.SimpleNamespace(device=device,cache_config=types.SimpleNamespace(kv_cache_memory_bytes=17*1024**3),
                _b12x_startup_coordinator=None,_b12x_profile_batch=None)
            @helper.release_after_explicit_profile
            def profile_stub(owner):
                if args.fixture=='current':
                    idle.clear();rows.append(sample('cached-inside-profile-stub'))
                torch.cuda.synchronize();return 17*1024**3
            failure=None
            try:profile_stub(worker)
            except RuntimeError as error:failure=str(error)
            rows.append(sample('after-helper-or-exception'))
            print('B12X_PINNED_RESIDENCY '+json.dumps(dict(fixture=args.fixture,
                comparison='fixture-only-under-current-common-setup',rows=rows,helper_sha256=helper_sha,
                helper_gate_passed=failure is None,helper_failure=failure,
                measurement_only=True,compound_probe_qualified=False,checkpoint_deployment_cleared=False,
                checkpoint_loaded=False,server_loaded=False,fixture_bytes=512*1024**2,
                added_waits=False,gate_interval_unchanged=True),separators=(',',':')),flush=True)
        finally:graph.reset();host_graph.reset()
    reset_workspace_manager()


if __name__=='__main__':main()
