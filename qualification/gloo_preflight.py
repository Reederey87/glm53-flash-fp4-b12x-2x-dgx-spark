"""CPU-only two-host Gloo route and collective preflight; no CUDA operations."""
import argparse
from datetime import timedelta
import json
import os
import socket
from urllib.parse import urlsplit

import torch
import torch.distributed as dist
from ignition.preparation.host_ranks import _use_interface

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--rank', type=int, choices=(0, 1), required=True)
p.add_argument('--rendezvous', default='tcp://192.168.177.10:29679')
a = p.parse_args()
address = urlsplit(a.rendezvous)
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as route:
    route.connect((address.hostname, address.port))
    local = route.getsockname()[0]
    _use_interface(local)
assert local == ('192.168.177.10' if a.rank == 0 else '192.168.177.11')
assert os.environ['GLOO_SOCKET_IFNAME'] == 'enp1s0f1np1'
dist.init_process_group('gloo', init_method=a.rendezvous, rank=a.rank, world_size=2,
                        timeout=timedelta(seconds=30))
try:
    value = torch.tensor([a.rank + 1], dtype=torch.int64, device='cpu')
    dist.all_reduce(value)
    assert value.item() == 3
    peers = [None, None]
    dist.all_gather_object(peers, {'rank': a.rank, 'address': local})
    assert peers == [{'rank': 0, 'address': '192.168.177.10'}, {'rank': 1, 'address': '192.168.177.11'}]
    dist.barrier()
    print(json.dumps({'rank': a.rank, 'local': local, 'interface': os.environ['GLOO_SOCKET_IFNAME'],
                      'all_reduce': value.item(), 'peers': peers, 'passed': True}), flush=True)
finally:
    dist.destroy_process_group()
