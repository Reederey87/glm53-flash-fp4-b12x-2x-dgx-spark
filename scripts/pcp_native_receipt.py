"""Compound micro proof; model-free entry is never a model-profile receipt."""
import json
import re
from check_pcp_native_cuda import PARENT_SHA,EXPECTED_STATE
from native_ownership_receipt import validate as validate_native
from pcp_bound_snapshot import validate as validate_policy

WORKER='cc95ace187a6ab535bb687c8bb97f5089a1f59dc6e1feb00ee799ff3ea5c40eb'
HELPER='1d4fac4c97fa2b197ef8238c41bcd935f0d361972b9711afdfc101080aee073b'
COLLECTOR='d79cadb46b957e8d4d69fb707b6839aacf832d0c89d72feaebb698d7d1252b02'


def validate(log,spelling,node,run_id):
    if node not in ('head','worker') or not re.fullmatch('[0-9a-f]{32}',run_id):raise ValueError('invalid expected invocation')
    def one(marker):
        rows=[(i,json.loads(l[len(marker):])) for i,l in enumerate(log.splitlines()) if l.startswith(marker)]
        if len(rows)!=1:raise ValueError('missing/duplicate '+marker)
        return rows[0]
    start,before=one('B12X_PCP_NATIVE_BEGIN ');end,after=one('B12X_PCP_NATIVE_END ')
    if (spelling not in ('indexed','unindexed') or before['device_spelling']!=spelling
            or before['scope']!='model-free-entry-not-model-profile' or start>=end):raise ValueError('wrong compound context')
    if before['parent_sha256']!=PARENT_SHA or after['parent_sha256']!=PARENT_SHA or before['pid']!=after['pid']:
        raise ValueError('compound source/process mismatch')
    if any(after[k] is not False for k in ('checkpoint_loaded','server_loaded','checkpoint_deployment_cleared')):
        raise ValueError('unsupported checkpoint claim')
    for row in (before,after):
        if row['allocator_state']!=EXPECTED_STATE or any(type(row['allocator_state'][k]) is not type(v) for k,v in EXPECTED_STATE.items()):
            raise ValueError('allocator/source/device state drift')
        if row['node']!=node or row['run_id']!=run_id or row['device_spelling']!=spelling:
            raise ValueError('cross-node/spelling/invocation evidence')
        if row['kernel']['settings_read_only']['percpu_pagelist_high_fraction']!='512':raise ValueError('policy drift')
        validate_policy(row['kernel'],512)
    summaries=[(i,json.loads(l)) for i,l in enumerate(log.splitlines()) if l.startswith('{') and '"terminal_collector"' in l]
    if len(summaries)!=1:raise ValueError('missing/duplicate compound graph summary')
    position,summary=summaries[0]
    if not start<position<end or summary['pid']!=before['pid'] or summary['device']!=('cuda:0' if spelling=='indexed' else 'cuda'):
        raise ValueError('wrong graph process/device/order')
    for i,line in enumerate(log.splitlines()):
        if any(marker in line for marker in ('B12X_PINNED_RETURN ','B12X_NATIVE_OWNERS ','B12X_HOST_OWNERSHIP ')):
            if not start<i<position:raise ValueError('compound proof outside probe/graph boundaries')
    for k in ('terminal_collector','common_pinned_return_completed','pointers_preserved','compiler_and_loader_forbidden','admission_stub_not_model_profile'):
        if summary[k] is not True:raise ValueError('compound graph/lifetime gate failed')
    if (summary['prepared_b12x_replays']!=3 or summary['pinned_copy_replays']!=3
            or summary['checkpoint_loaded'] is not False or summary['server_loaded'] is not False):raise ValueError('incomplete graph coverage')
    # Adapt only the real outer probe-entry timestamp to the validator's ordering
    # argument. This is not a loader/profile trace and cannot clear a model gate.
    proof=validate_native(log,WORKER,HELPER,COLLECTOR,{'pid':before['pid'],'records':[{'utc_ns':before['utc_ns']}]})
    if not before['utc_ns']<=proof['memory']['record']['utc_ns']<=after['utc_ns']:raise ValueError('compound timing mismatch')
    return dict(node=node,run_id=run_id,device_spelling=spelling,probe_entry_not_model_profile=True,native_inventory=proof['inventory'],
        pinned_return=proof['pinned_return'],graph_summary=summary,compound_micro_qualified=True,
        checkpoint_deployment_cleared=False,serving_qualified=False)
