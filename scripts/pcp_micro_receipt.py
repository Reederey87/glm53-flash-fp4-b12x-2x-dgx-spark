"""Separate complete measurement from the unchanged micro physical gate."""
import json
from pathlib import Path
import sys
from check_kernel_return_cuda import EXPECTED
from pinned_cache_receipt import validate as pin_validate
from pcp_bound_snapshot import validate as policy_validate

def validate(log,fraction):
    def one(prefix):
        rows=[json.loads(line[len(prefix):]) for line in log.splitlines() if line.startswith(prefix)]
        if len(rows)!=1:raise ValueError('incomplete/duplicate '+prefix)
        return rows[0]
    result=one('B12X_PCP_MICRO ');parent=one('B12X_HOST_REGISTER_MEMORY ')
    if result['fraction']!=fraction or result['source_parents']!=EXPECTED:raise ValueError('wrong arm/source')
    if any(result[k] is not False for k in ('checkpoint_deployment_cleared','checkpoint_loaded','server_loaded')):raise ValueError('unsupported model clearance')
    if parent['mode']!='default' or parent['effective_allocator_settings']!='':raise ValueError('host backend drift')
    for key in ('live_state_unchanged','effective_settings_preserved','pointers_preserved','compiler_loader_forbidden_during_replay'):
        if parent[key] is not True:raise ValueError('live replay gate failed')
    if parent['prepared_b12x_graph_replays']!=3 or parent['pinned_copy_replays']!=3:raise ValueError('replay coverage incomplete')
    phases=['before-fixture','resident-fixture','cached-before-helper','after-helper-or-exception']
    if [r['phase'] for r in result['bundles']]!=phases or [r['phase'] for r in parent['rows']]!=phases:raise ValueError('wrong phase coverage')
    pid=parent['rows'][0]['pid']
    for bundle,row in zip(result['bundles'],parent['rows']):
        if bundle['process_sample']!=row or row['pid']!=pid:raise ValueError('source process/row mismatch')
        if bundle['kernel']['settings_read_only']['percpu_pagelist_high_fraction']!=str(fraction):raise ValueError('policy drift')
        policy_validate(bundle['kernel'],fraction)
    allocation=result['fixture_allocation']
    if allocation['bytes']!=512*1024**2 or allocation['end_ns']<allocation['begin_ns']:raise ValueError('invalid fixture latency')
    failure=None
    try:
        proof=pin_validate(log,'ea6dc50f79cea69ab42d0fe31982a301b1081aa5f3f79eb268edb4df943b143e',
            '1761e9aeb863da2cb307fc7094c30af495aa78ff9e135e9d58d81df7b6c82ac6',{'pid':pid,'records':[{'utc_ns':0}]})
    except ValueError as error:failure=str(error);proof=None
    qualified=failure is None
    if parent['helper_gate_passed'] is not qualified or parent['micro_physical_and_graph_qualified'] is not qualified:
        raise ValueError('parent/helper classification differs')
    return dict(fraction=fraction,pid=pid,micro_qualified=qualified,failure=failure,pinned_proof=proof,
        allocation_plus_fill_ns=allocation['end_ns']-allocation['begin_ns'],checkpoint_deployment_cleared=False)

if __name__=='__main__':
    root=Path(sys.argv[1]);out={}
    for node in ('head','worker'):
        for arm,fraction in (('A',0),('B',512)):
            out[node+'-'+arm]=validate((root/(node+'-'+arm+'.log')).read_text(),fraction)
    (root/'outcome.json').write_text(json.dumps(out,indent=2)+'\n')
    if not all(out[node+'-B']['micro_qualified'] for node in ('head','worker')):raise ValueError('PCP B physical micro gate failed; model remains uncleared')
    print('PCP micro only passed; checkpoint deployment is not cleared')
