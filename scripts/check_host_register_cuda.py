"""Tiny capability/lifetime check only; no physical-return qualification."""
import json
import re
import torch
from cuda.bindings import runtime


def main():
    torch.cuda.init();device=torch.cuda.current_device()
    attrs={}
    for name in ('cudaDevAttrHostRegisterSupported','cudaDevAttrPageableMemoryAccessUsesHostPageTables',
                 'cudaDevAttrCanUseHostPointerForRegisteredMem','cudaDevAttrUnifiedAddressing','cudaDevAttrIntegrated'):
        status,value=runtime.cudaDeviceGetAttribute(getattr(runtime.cudaDeviceAttr,name),device)
        if int(status)!=0:raise RuntimeError('CUDA attribute query failed: '+name)
        attrs[name]=int(value)
    print('B12X_HOST_REGISTER_CAPABILITIES '+json.dumps(attrs),flush=True)
    if attrs['cudaDevAttrHostRegisterSupported']!=1 or attrs['cudaDevAttrIntegrated']!=1 or attrs['cudaDevAttrUnifiedAddressing']!=1:
        raise RuntimeError('registered-host microexperiment requires supported integrated UVA device')
    effective=torch._C._accelerator_getAllocatorSettings()
    if not re.search(r'(?:^|,)\s*pinned_use_cuda_host_register\s*:\s*True\s*(?:,|$)',effective):
        raise RuntimeError('registered-host treatment not active in effective allocator settings')
    graph=torch.cuda.CUDAGraph()
    pinned=torch.empty(4096,dtype=torch.uint8,pin_memory=True);pinned.fill_(17)
    output=torch.empty_like(pinned,device=f'cuda:{device}')
    try:
        with torch.cuda.graph(graph):output.copy_(pinned,non_blocking=True)
        torch.cuda.synchronize()
        pointers=(pinned.data_ptr(),output.data_ptr())
        idle=torch.empty(65536,dtype=torch.uint8,pin_memory=True);idle.fill_(37);del idle
        torch.cuda.synchronize()
        before=torch.cuda.memory.host_memory_stats()
        live=(torch.cuda.memory_allocated(),torch.cuda.memory_reserved())
        torch.accelerator.memory.empty_host_cache()
        after=torch.cuda.memory.host_memory_stats()
        if (before['allocated_bytes.current']-after['allocated_bytes.current']<65536
                or before['active_bytes.current']!=after['active_bytes.current']
                or after['num_host_free']<=before['num_host_free']
                or live!=(torch.cuda.memory_allocated(),torch.cuda.memory_reserved())):
            raise RuntimeError('registered-host tiny release changed live graph state or did not retire idle block')
        for value in (3,7,11):
            pinned.fill_(value);output.zero_();graph.replay();torch.cuda.synchronize()
            assert torch.equal(output,torch.full_like(output,value))
        assert pointers==(pinned.data_ptr(),output.data_ptr())
        print(json.dumps(dict(tiny_capability_and_lifetime_only=True,attributes=attrs,effective_allocator_settings=effective,
            pageable_host_table_registration=bool(attrs['cudaDevAttrPageableMemoryAccessUsesHostPageTables']),
            os_page_locking_proven=False,active_bytes_unchanged=True,graph_replays=3,pointers_preserved=True,
            retired_idle_bytes=before['allocated_bytes.current']-after['allocated_bytes.current'],
            physical_return_qualified=False,checkpoint_deployment_cleared=False,checkpoint_loaded=False,server_loaded=False)),flush=True)
    finally:graph.reset()


if __name__=='__main__':main()
