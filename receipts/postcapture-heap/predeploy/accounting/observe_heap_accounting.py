import argparse,ctypes,json,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--mode',choices=('trim','control'),required=True);a=p.parse_args()
libc=ctypes.CDLL(None)
libc.malloc.argtypes=(ctypes.c_size_t,);libc.malloc.restype=ctypes.c_void_p
libc.free.argtypes=(ctypes.c_void_p,);libc.free.restype=None
libc.malloc_trim.argtypes=(ctypes.c_size_t,);libc.malloc_trim.restype=ctypes.c_int

def sample(phase):
 d=dict(phase=phase,t=time.monotonic_ns())
 for file,keys in [('/proc/meminfo',('MemFree','MemAvailable')),('/proc/self/status',('RssAnon',))]:
  for line in Path(file).read_text().splitlines():
   k,_,v=line.partition(':')
   if k in keys:d[k]=int(v.split()[0])*1024
 if d['MemAvailable']<2*1024**3:raise RuntimeError('independent floor failed')
 return d

def observe(phase,seconds):
 started=time.monotonic_ns()
 while True:
  rows.append(sample(phase));elapsed=(time.monotonic_ns()-started)/1e9
  if elapsed>=seconds:
   if elapsed>seconds+.5:raise RuntimeError('observation deadline violation')
   return
  time.sleep(min(.05,seconds-elapsed))
rows=[sample('initial')];blocks=[]
try:
 for n in range(8192):
  q=libc.malloc(65536)
  if not q:raise MemoryError('fixture')
  blocks.append(q);ctypes.memset(q,37,65536)
 observe('allocated-resident',1.25)
 for n,q in enumerate(blocks):
  if n%64 and n!=8191:libc.free(q);blocks[n]=None
 rows.append(sample('before'));returned=libc.malloc_trim(0) if a.mode=='trim' else None
 rows.append(sample('immediate'));observe('after-observe',3.)
 print(json.dumps(dict(mode=a.mode,trim_result=returned,fixture_bytes=8192*65536,rows=rows)))
finally:
 for q in blocks:
  if q is not None:libc.free(q)
