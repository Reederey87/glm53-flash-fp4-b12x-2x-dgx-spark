"""Same fixture under a preregistered PCP policy; no model qualification."""
import hashlib
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch
import kernel_memory_counters as counters
from pcp_bound_snapshot import validate as validate_policy
from check_kernel_return_cuda import EXPECTED


def main():
    if sys.argv[1:] not in (['--fraction','0'],['--fraction','512']):raise ValueError('unregistered arm')
    fraction=int(sys.argv[2])
    for name,expected in EXPECTED.items():
        if hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()!=expected:
            raise ValueError('parent source changed')
    import check_host_register_memory_cuda as parent
    original_sample=parent.sample;original_ones=parent.torch.ones;bundles=[];allocation=[]
    def sample(phase):
        row=original_sample(phase)
        if len(bundles)>=4:raise ValueError('too many counter bundles')
        kernel=validate_policy(counters.snapshot(fraction),fraction)
        bundles.append(dict(phase=phase,process_sample=row,kernel=kernel))
        return row
    def ones(*args,**kw):
        fixture=args==(512*1024**2,) and kw=={'dtype':parent.torch.uint8,'pin_memory':True}
        begin=time.monotonic_ns();result=original_ones(*args,**kw);end=time.monotonic_ns()
        if fixture:allocation.append(dict(begin_ns=begin,end_ns=end,bytes=result.numel()*result.element_size()))
        return result
    # Parent remains byte-identical and sees the same sealed default host backend.
    sys.argv=[sys.argv[0],'--mode','default']
    with patch.object(parent,'sample',side_effect=sample),patch.object(parent.torch,'ones',side_effect=ones):parent.main()
    if [r['phase'] for r in bundles]!=['before-fixture','resident-fixture','cached-before-helper','after-helper-or-exception']:
        raise ValueError('incomplete phase coverage')
    if len(allocation)!=1 or allocation[0]['bytes']!=512*1024**2:raise ValueError('fixture allocation coverage differs')
    print('B12X_PCP_MICRO '+json.dumps(dict(fraction=fraction,bundles=bundles,fixture_allocation=allocation[0],
        source_parents=EXPECTED,checkpoint_deployment_cleared=False,checkpoint_loaded=False,server_loaded=False),separators=(',',':')),flush=True)


if __name__=='__main__':main()
