"""Inspect a complete one-rep native mixed trace; never a performance verdict.

Usage from any directory: uv run python qualification/analyze_mixed_trace.py DIR POLICY
DIR contains POLICY-mixed.jsonl and POLICY-trace.jsonl. The retained untraced
reference stays in this repository. Output is POLICY-analysis.json beside inputs.
No HTTP-to-native-slot identity is asserted. GPU durations are observations,
not inferred GPU start/end timestamps; completion gaps are not per-token gaps.
"""
import json,sys,collections
from pathlib import Path
repo=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(repo/'scripts'))
from flare_mixed_compare import load,load_diagnostic
from flare_trace_check import integer
root=Path(sys.argv[1]); policy=sys.argv[2]
manifest,requests,cases=load_diagnostic(root/f'{policy}-mixed.jsonl',policy)
reference=(repo/'receipts/flare-qualification-20261115')/('scheduler-balanced-mixed.jsonl' if policy=='balanced' else 'latency-mixed.jsonl')
_,original,_=load(reference,policy)
assert all(r['input_sha256']==original[k]['input_sha256'] for k,r in requests.items())
rows=[json.loads(x) for x in (root/f'{policy}-trace.jsonl').read_text().splitlines()]
header,end=rows[0],rows[-1]
assert header['event']=='manifest' and header['schema']==1
assert end['event']=='complete' and end['complete'] is True and end['truncated'] is False and end['dropped_updates']==0
assert end['reason'] in ('stopped','duration')
graphs={g['graph']:g for g in header['graphs']}
assert len(graphs)==len(header['graphs'])
completions=[];prefills=collections.defaultdict(list);decode=collections.defaultdict(list);states=collections.defaultdict(list)
fence,at=-1,header['started_at_ns']
for r in rows[1:-1]:
 if r['event']=='state':
  for q in r['requests']:states[q['slot'],q['generation']].append(dict(q,at_ns=r['sampled_at_ns']))
  continue
 assert r['event']=='completion' and r['graph'] in graphs
 assert all(integer(r[k]) for k in ('fence','at_ns','selected_at_ns','commit_ns','wall_ns'))
 assert fence<r['fence'] and at<=r['at_ns'] and r['selected_at_ns']<=r['commit_ns']<=r['at_ns']
 assert r['gpu_ns'] is None or integer(r['gpu_ns'],1)
 fence,at=r['fence'],r['at_ns'];completions.append(r)
 seen=set()
 for l in r['lanes']:
  assert integer(l['slot']) and l['slot']<64 and integer(l['generation'],1)
  assert integer(l['start_position']) and integer(l['tokens']) and l['slot'] not in seen
  seen.add(l['slot']); key=l['slot'],l['generation'];kind=graphs[r['graph']]['kind']
  if kind=='Prefill':
   assert l['tokens']>0
   prefills[key].append(dict(r,**l))
  elif kind in ('Speculative','Decode'):decode[key].append(r)
assert end['completions']==len(completions) and end['at_ns']>=at
assert [r['fence'] for r in completions]==list(range(1,len(completions)+1))
histories=[]
for key,events in prefills.items():
 position=0
 for e in events:
  assert e['start_position']==position,(key,position,e)
  position+=e['tokens']
 known={s['prompt'] for s in states[key]}
 assert not known or known=={position},(key,known,position)
 histories.append({'request':list(key),'prompt_tokens':position,'first_selected_s':events[0]['selected_at_ns']/1e9,'finish_s':events[-1]['at_ns']/1e9,'prefill_graphs':len(events),'max_gpu_s':max((e['gpu_ns'] or 0)/1e9 for e in events),'max_wall_s':max(e['wall_ns']/1e9 for e in events),'first_observed_s':min((s['at_ns']/1e9 for s in states[key]),default=None),'last_chunks':[{'graph':graphs[e['graph']]['name'],'selected_s':e['selected_at_ns']/1e9,'complete_s':e['at_ns']/1e9,'start_position':e['start_position'],'tokens':e['tokens'],'gpu_s':(e['gpu_ns'] or 0)/1e9} for e in events[-3:]]})
assert collections.Counter(h['prompt_tokens'] for h in histories)==collections.Counter([128]+[r['prompt_tokens'] for r in requests.values()])
longs=sorted((h for h in histories if h['prompt_tokens']==131072),key=lambda h:h['first_selected_s'])
assert len(longs)==2
start=longs[1]['finish_s']
# The last case starts only after the long+short-arrivals case completes.
# Report graph completions, not assumed token emission or HTTP request IDs.
overlap=[h for h in histories if h['first_selected_s']>start]
interval=(min(h['first_selected_s'] for h in overlap if h['prompt_tokens']>=4096),max(h['finish_s'] for h in overlap if h['prompt_tokens']>=4096))
steps=[r for r in completions if interval[0]<=r['at_ns']/1e9<=interval[1]]
report={'policy':policy,'scope':'one-repetition diagnostic; native generations not mapped to HTTP IDs; graph gaps are not output-token gaps','matched_requests':len(requests),'complete_native_histories':len(histories),'native_completions':len(completions),'total_prompt_tokens':sum(h['prompt_tokens'] for h in histories),'histories':histories,'decode_overlap_interval_s':interval,'overlap_graphs':{},'decode_completion_gaps':[]}
for graph in sorted({r['graph'] for r in steps}):
 group=[r for r in steps if r['graph']==graph]
 report['overlap_graphs'][graphs[graph]['name']]={'count':len(group),'gpu_s':[r['gpu_ns']/1e9 if r['gpu_ns'] else None for r in group],'wall_s':[r['wall_ns']/1e9 for r in group]}
for key,events in decode.items():
 ds=[e for e in events if e['at_ns']/1e9>start]
 if len(ds)<2:continue
 a,b=max(zip(ds,ds[1:]),key=lambda ab:ab[1]['at_ns']-ab[0]['at_ns'])
 between=[{'graph':graphs[r['graph']]['name'],'gpu_s':r['gpu_ns']/1e9 if r['gpu_ns'] else None,'wall_s':r['wall_ns']/1e9,'fence':r['fence'],'timing_origin':r['timing_origin'],'estimate_s':r['estimate_ns']/1e9,'selected_s':r['selected_at_ns']/1e9,'complete_s':r['at_ns']/1e9,'lanes':r['lanes']} for r in completions if a['fence']<r['fence']<=b['fence']]
 report['decode_completion_gaps'].append({'request':list(key),'max_gap_s':(b['at_ns']-a['at_ns'])/1e9,'between':between})
(root/f'{policy}-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('histories','overlap_graphs')},indent=2))
print('short histories',json.dumps([h for h in histories if h['prompt_tokens']==1024][-3:],indent=2))
print('overlap graph counts', {k:v['count'] for k,v in report['overlap_graphs'].items()})
