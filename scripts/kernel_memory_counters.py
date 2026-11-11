"""Bounded ordinary proc counters. No refresh, draining, allocator or writes."""
import os
import re
import time

CAPS={'meminfo':32768,'vmstat':65536,'zoneinfo':262144,'buddyinfo':32768}
MEM=('MemFree','MemAvailable','Cached','AnonPages','Shmem','Slab','SReclaimable',
     'Unevictable','Active(file)','Inactive(file)','KReclaimable')
PCP=('count','high','batch','high_min','high_max','stat_threshold')
PGALLOC={'pgalloc_'+name for name in ('dma','dma32','normal','movable','device')}
# Both installed kernel configs have CONFIG_ARCH_FORCE_MAX_ORDER=13.
NR_PAGE_ORDERS=14


def bounded(path,maximum):
    with open(path) as stream:value=stream.read(maximum+1)
    if len(value)>maximum:raise ValueError('proc read exceeds bound')
    return value


def parse_meminfo(text):
    result={}
    for line in text.splitlines():
        name,_,rest=line.partition(':')
        if name in MEM:
            if name in result or not re.fullmatch(r'\s*\d+ kB\s*',rest):raise ValueError('invalid/duplicate meminfo field')
            result[name]=int(rest.split()[0])*1024
    if set(result)!=set(MEM):raise ValueError('missing meminfo fields')
    return result


def parse_vmstat(text):
    result={}
    for line in text.splitlines():
        fields=line.split()
        if len(fields)!=2:raise ValueError('invalid vmstat line')
        name,value=fields
        if name in ('nr_free_pages','nr_anon_pages','nr_shmem','nr_active_file','nr_inactive_file','pgfree') or name.startswith('pgalloc_'):
            if name in result or not value.isdecimal():raise ValueError('invalid/duplicate vmstat field')
            result[name]=int(value)
    if not {'nr_free_pages','nr_anon_pages','nr_shmem','nr_active_file','nr_inactive_file','pgfree',*PGALLOC}<=set(result):
        raise ValueError('missing vmstat fields')
    if {name for name in result if name.startswith('pgalloc_')}!=PGALLOC:
        raise ValueError('unexpected PGALLOC schema')
    return result


def parse_zoneinfo(text,online):
    zones=[];zone=None;cpu=None;seen=set();rows=0
    for line in text.splitlines():
        head=re.fullmatch(r'Node\s+(\d+),\s+zone\s+(\S+)\s*',line)
        if head:
            key=(int(head[1]),head[2])
            if key in seen or len(zones)>=256:raise ValueError('duplicate/excessive zones')
            seen.add(key);zone=dict(node=key[0],name=key[1],cpus=[]);zones.append(zone);cpu=None;continue
        if zone is None:continue
        value=re.fullmatch(r'\s*(pages free|managed|present)\s+(\d+)\s*',line)
        if value:
            name={'pages free':'free_pages_reported','managed':'managed_pages','present':'present_pages'}[value[1]]
            if name in zone:raise ValueError('duplicate zone page count')
            zone[name]=int(value[2]);continue
        processor=re.fullmatch(r'\s*cpu:\s*(\d+)\s*',line)
        if processor:
            rows+=1
            if rows>8192:raise ValueError('too many PCP rows')
            cpu=dict(cpu=int(processor[1]));zone['cpus'].append(cpu);continue
        field=re.fullmatch(r'\s*(count|high|batch|high_min|high_max|vm stats threshold):\s*(\d+)\s*',line)
        if field and cpu is not None:
            name='stat_threshold' if field[1]=='vm stats threshold' else field[1]
            if name in cpu:raise ValueError('duplicate PCP field')
            cpu[name]=int(field[2])
    if not zones:raise ValueError('no zones')
    for z in zones:
        if not {'free_pages_reported','managed_pages','present_pages'}<=set(z):raise ValueError('missing zone counts')
        if z['present_pages']:
            if {r['cpu'] for r in z['cpus']}!=set(online) or len(z['cpus'])!=len(online):
                raise ValueError('missing/duplicate online CPU pagesets')
            if any(set(r)!={'cpu',*PCP} for r in z['cpus']):raise ValueError('missing PCP fields')
        elif z['cpus']:raise ValueError('unexpected pagesets in unpopulated zone')
    # Count can legitimately exceed high on the deployed kernel's TRYLOCK path.
    return zones


def parse_buddyinfo(text):
    rows=[];seen=set();orders=None
    for line in text.splitlines():
        match=re.fullmatch(r'Node\s+(\d+),\s+zone\s+(\S+)\s+([\d\s]+)',line)
        if not match:raise ValueError('invalid buddyinfo row')
        key=(int(match[1]),match[2]);counts=[int(v) for v in match[3].split()]
        if key in seen or len(rows)>=256 or len(counts)!=NR_PAGE_ORDERS:raise ValueError('invalid/duplicate buddy zone/order count')
        if orders is not None and len(counts)!=orders:raise ValueError('inconsistent buddy order count')
        orders=len(counts);seen.add(key);rows.append(dict(node=key[0],name=key[1],free_blocks=counts))
    if not rows:raise ValueError('no buddy zones')
    return rows


def online_cpus(text):
    result=set()
    for part in text.strip().split(','):
        if not re.fullmatch(r'\d+(?:-\d+)?',part):raise ValueError('invalid CPU list')
        ends=[int(v) for v in part.split('-')];start=ends[0];stop=ends[-1]
        if not 0<=start<=stop<4096:raise ValueError('CPU range outside bound')
        values=set(range(start,stop+1))
        if result&values:raise ValueError('duplicate CPU list entry')
        result|=values
    return sorted(result)


def snapshot():
    started=time.monotonic_ns();timings={};raw={}
    page_size=os.sysconf('SC_PAGE_SIZE')
    cpus=online_cpus(bounded('/sys/devices/system/cpu/online',4096))
    for name,cap in CAPS.items():
        begin=time.monotonic_ns();raw[name]=bounded('/proc/'+name,cap)
        timings[name]=dict(begin_ns=begin,end_ns=time.monotonic_ns())
    settings={name:bounded('/proc/sys/vm/'+name,128).strip() for name in ('min_free_kbytes','stat_interval','percpu_pagelist_high_fraction')}
    if settings!={'min_free_kbytes':'1048576','stat_interval':'1','percpu_pagelist_high_fraction':'0'}:
        raise ValueError('kernel counter study controls changed')
    zones=parse_zoneinfo(raw['zoneinfo'],cpus);buddy=parse_buddyinfo(raw['buddyinfo'])
    populated={(z['node'],z['name']) for z in zones if z['present_pages']}
    if {(z['node'],z['name']) for z in buddy}!=populated:raise ValueError('buddy/zone coverage mismatch')
    pcp=sum(r['count'] for z in zones for r in z['cpus'])
    free_buddy=sum(sum(n<<order for order,n in enumerate(z['free_blocks'])) for z in buddy)
    result=dict(version=1,kernel=os.uname().release,page_size=page_size,online_cpus=cpus,
        begin_ns=started,per_file_timing=timings,
        meminfo_bytes=parse_meminfo(raw['meminfo']),vmstat_base_page_counters=parse_vmstat(raw['vmstat']),
        zones=zones,buddy=buddy,pcp_count_bytes=pcp*page_size,buddy_list_bytes=free_buddy*page_size,
        settings_read_only=settings,atomic_snapshot=False,stat_refresh_read=False,
        settings_written=False,available_headroom_qualified=False)
    result['end_ns']=time.monotonic_ns()
    if result['kernel']!='6.17.0-1031-nvidia' or result['end_ns']-started>1_000_000_000:
        raise ValueError('wrong kernel or counter bundle exceeded1s')
    return result
