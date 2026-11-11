"""Validate policy activation without requiring immediate stock/high draining."""
import json
from pathlib import Path
import sys
import kernel_memory_counters as counters


def validate(row,fraction):
    if row['meminfo_bytes']['MemAvailable']<100*1024**3:raise ValueError('model-free study requires100GiB headroom')
    if row['page_size']!=4096 or row['online_cpus']!=list(range(20)):raise ValueError('topology/page size changed')
    populated=[z for z in row['zones'] if z['present_pages']]
    if {(z['node'],z['name']) for z in populated}!={(0,'DMA'),(0,'Normal')}:raise ValueError('zone topology changed')
    if Path('/sys/devices/system/node/node0/cpulist').read_text().strip()!='0-19':raise ValueError('local CPU topology changed')
    for z in populated:
        expected_batch=31 if z['name']=='DMA' else 63
        expected_managed=(174798,174814) if z['name']=='DMA' else (31725389,)
        if z['managed_pages'] not in expected_managed:raise ValueError('managed page control changed')
        for cpu in z['cpus']:
            if cpu['batch']!=expected_batch:raise ValueError('base batch changed')
            if fraction==512:
                expected=max(z['managed_pages']//512//20,4*expected_batch)
                if cpu['high_min']!=expected or cpu['high_max']!=expected:raise ValueError('cap did not activate')
            elif cpu['high_min']>=cpu['high_max']:raise ValueError('adaptive bounds not restored')
    return row


if __name__=='__main__':
    if sys.argv[1:] not in (['0'],['512']):raise ValueError('unregistered snapshot arm')
    fraction=int(sys.argv[1]);print('B12X_PCP_SNAPSHOT '+json.dumps(validate(counters.snapshot(fraction),fraction),separators=(',',':')),flush=True)
