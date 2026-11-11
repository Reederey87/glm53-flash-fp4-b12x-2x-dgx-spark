import json,os,re,stat,time
from pathlib import Path
def read(path,maximum=1024**2):
    with open(path) as stream:
        value=stream.read(maximum+1)
    if len(value)>maximum:raise ValueError('counter file exceeds bound')
    return value
mem={}
for line in read('/proc/meminfo').splitlines():
    key,_,value=line.partition(':')
    if key in ('MemTotal','MemFree','MemAvailable','Cached','AnonPages','Shmem','Slab','SReclaimable','Unevictable','CmaTotal','CmaFree','SwapTotal','SwapFree'):
        mem[key]=int(value.split()[0])*1024
vm={}
for line in read('/proc/vmstat').splitlines():
    key,value=line.split()
    if key in ('nr_free_pages','nr_anon_pages','nr_shmem','nr_active_file','nr_inactive_file','nr_free_cma'):
        vm[key]=int(value)
zones=[];zone=None;cpu=None
for line in read('/proc/zoneinfo').splitlines():
    header=re.match(r'Node\s+(\d+),\s+zone\s+(\S+)',line)
    if header:
        zone=dict(node=int(header[1]),name=header[2],cpus=[]);zones.append(zone);cpu=None;continue
    if zone is None:continue
    free=re.match(r'\s*pages free\s+(\d+)',line)
    if free:zone['free_pages_reported']=int(free[1]);continue
    processor=re.match(r'\s*cpu:\s*(\d+)',line)
    if processor:cpu=dict(cpu=int(processor[1]));zone['cpus'].append(cpu);continue
    field=re.match(r'\s*(count|high|batch|high_min|high_max|stat_threshold):\s*(\d+)',line)
    if field and cpu is not None:cpu[field[1]]=int(field[2])
settings={name:read('/proc/sys/vm/'+name,128).strip() for name in ('min_free_kbytes','stat_interval','percpu_pagelist_high_fraction')}
refresh=os.stat('/proc/sys/vm/stat_refresh')
print(json.dumps(dict(utc_ns=time.time_ns(),kernel=os.uname().release,page_size=os.sysconf('SC_PAGE_SIZE'),
    meminfo_bytes=mem,vmstat_base_page_counters=vm,zones=zones,settings_read_only=settings,
    stat_refresh_metadata_only=dict(mode=oct(stat.S_IMODE(refresh.st_mode)),uid=refresh.st_uid),
    stat_refresh_content_read=False,no_settings_written=True,no_allocator_calls=True),indent=2))
