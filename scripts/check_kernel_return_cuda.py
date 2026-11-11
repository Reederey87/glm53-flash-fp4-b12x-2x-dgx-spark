"""Observational wrapper only: untouched default helper with PCP/buddy bundles."""
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch
import kernel_memory_counters as counters

ROOT=Path(__file__).resolve().parent
EXPECTED={'check_host_register_memory_cuda.py':'83f453006fc9aff77ec75a23a0a92cf5c58ad1ad68fd6fd3df5f37184c859642',
          'check_pinned_residency_cuda.py':'8e4e1a86aecc164d02fd8890951ab453adacf2eda4cf5d263d820480babf71ce'}


def main():
    if sys.argv[1:]!=['--mode','default']:raise ValueError('sealed default-backend observational study')
    for name,expected in EXPECTED.items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected:raise ValueError('parent measurement source changed')
    import check_host_register_memory_cuda as parent
    original=parent.sample;bundles=[]
    def sample(phase):
        row=original(phase)
        if phase in ('cached-before-helper','after-helper-or-exception'):
            if len(bundles)>=2:raise ValueError('unexpected repeated counter collection')
            bundles.append(dict(phase=phase,process_sample=row,kernel=counters.snapshot()))
        return row
    with patch.object(parent,'sample',side_effect=sample):parent.main()
    if [r['phase'] for r in bundles]!=['cached-before-helper','after-helper-or-exception']:
        raise ValueError('incomplete paired counter bundles')
    print('B12X_KERNEL_RETURN '+json.dumps(dict(scope='counter-observation-only',bundles=bundles,
        unchanged_parent_sources=EXPECTED,original_failures_remain_failed=True,candidate_qualified=False,
        checkpoint_deployment_cleared=False,checkpoint_loaded=False,server_loaded=False),separators=(',',':')),flush=True)


if __name__=='__main__':main()
