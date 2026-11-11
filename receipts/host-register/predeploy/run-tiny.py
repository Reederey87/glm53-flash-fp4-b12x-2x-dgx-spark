"""Enforce the reviewed tiny probe's process-start execution conditions."""
import os
import runpy
import sys

expected='pinned_use_cuda_host_register:True'
if (os.environ.get('PYTORCH_CUDA_ALLOC_CONF')!=expected
        or os.environ.get('PYTORCH_ALLOC_CONF') or os.environ.get('PYTORCH_HIP_ALLOC_CONF')
        or sys.flags.optimize!=0):
    raise RuntimeError('unexpected allocator environment or optimized interpreter')
import torch
if torch.version.git_version!='cf30153c4c131c8164ee7798e5022d810682e2cb':
    raise RuntimeError('wrong Torch source revision')
if torch.cuda.memory.get_allocator_backend()!='native':
    raise RuntimeError('tiny probe requires unchanged native device allocator')
runpy.run_path('/probe/scripts/check_host_register_cuda.py',run_name='__main__')
