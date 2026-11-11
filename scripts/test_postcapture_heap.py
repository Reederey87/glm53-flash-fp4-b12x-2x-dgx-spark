"""Postcapture heap return must preserve captures and reject weak reclamation."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from postcapture_heap_receipt import validate, MARKER, PROVIDERS

ROOT = Path(__file__).resolve().parent.parent


def load():
    sp=importlib.util.spec_from_file_location('heap_return',ROOT/'mods/postcapture-heap/return_heap.py')
    m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m


def record(phase):
    return dict(version=1,phase=phase,boundary='post-capture-before-second-warmup',pid=1,utc_ns=10,
        device_index=0,result=-17,kv_bytes=17*1024**3,fraction=1.,allocated=10,reserved=20,
        pinned_owned=5,pinned_active=2,gc_enabled=True,frozen_objects=0,workspace_locked=True,
        retained_program_owners=1,retained_identity_sha256='a'*64,runner_sha256='r',helper_sha256='h',
        heap=dict(arenas=2,free_chunk_bytes=1024**3,system_current_bytes=2*1024**3,mmap_bytes=0),
        process=dict(RssAnon=(3 if phase=='before' else 1)*1024**3),
        host=dict(MemAvailable=8*1024**3+(512*1024**2 if phase=='after' else 0)),elapsed_ns=1,trim_result=1,**PROVIDERS)


def proof(rows, prefix='Graph capturing finished\n'):
    return validate(prefix+''.join(MARKER+json.dumps(r)+'\n' for r in rows),'r','h',dict(pid=1,records=[dict(utc_ns=1)]))


class PostcaptureHeap(unittest.TestCase):
    def execute(self, *, request=17*1024**3, capture=False, fraction=1., original_failure=False, free=True, returned=True, locked=True):
        m=load();self.events=[];rows=[];state=dict(needs=True)
        def original(runner):
            self.events.append('capture')
            if original_failure:raise RuntimeError('original failed')
            state['needs']=False;return -17
        def trim(pad):self.assertEqual(pad,0);self.events.append('trim');return 1
        cuda=types.SimpleNamespace(is_initialized=lambda:True,current_device=lambda:0,is_current_stream_capturing=lambda:capture,
            memory=types.SimpleNamespace(get_allocator_backend=lambda:'native',get_per_process_memory_fraction=lambda d:fraction))
        platform=types.SimpleNamespace(current_platform=types.SimpleNamespace(is_integrated_gpu=lambda d:True))
        runner=types.SimpleNamespace(device=types.SimpleNamespace(type='cuda',index=None),
            cache_config=types.SimpleNamespace(kv_cache_memory_bytes=request),cudagraph_manager=types.SimpleNamespace(needs_capture=lambda:state['needs']))
        a,b=record('before'),record('after');a['workspace_locked']=b['workspace_locked']=locked
        if not free:a['heap']['free_chunk_bytes']=1
        if not returned:b['process']['RssAnon']=a['process']['RssAnon']
        with patch.dict(sys.modules,{'torch':types.SimpleNamespace(cuda=cuda),'vllm.platforms':platform}),patch.object(m,'providers',return_value=(None,None,{})),patch.object(m,'libc_api',return_value=types.SimpleNamespace(malloc_trim=trim)),patch.object(m,'snapshot',side_effect=[a,b]),patch.object(m,'emit',side_effect=rows.append):
            wrapped=m.return_heap_after_capture(original);result=wrapped(runner)
            with self.assertRaisesRegex(RuntimeError,'startup-once'):wrapped(runner)
        return result,rows

    def test_original_metric_preserved_and_one_trim(self):
        result,rows=self.execute();self.assertEqual(result,-17);self.assertEqual(self.events,['capture','trim'])
        self.assertEqual(proof(rows)['reclaimed_anon_bytes'],2*1024**3)

    def test_original_failure_and_wrong_request_never_trim(self):
        with self.assertRaisesRegex(RuntimeError,'explicit17G'):self.execute(request=None)
        self.assertEqual(self.events,[])
        with self.assertRaisesRegex(RuntimeError,'original failed'):self.execute(original_failure=True)
        self.assertEqual(self.events,['capture'])

    def test_profile_only_passthrough_does_not_mark_real_capture(self):
        m=load();runner=types.SimpleNamespace()
        @m.return_heap_after_capture
        def original(owner, *, profile_only=False):return -31
        self.assertEqual(original(runner,profile_only=True),-31)
        self.assertFalse(hasattr(runner,'_b12x_postcapture_heap_seen'))

    def test_capture_fraction_lock_and_free_heap_guards(self):
        for options in ({'capture':True},{'fraction':.8},{'locked':False},{'free':False}):
            with self.assertRaises(RuntimeError):self.execute(**options)
            self.assertEqual(self.events,['capture'])
        with self.assertRaisesRegex(RuntimeError,'failed256MiB'):self.execute(returned=False)

    def test_aggregate_heap_parsing_does_not_double_count_arenas(self):
        m=load();data='<malloc version="1"><heap nr="0"><total type="rest" size="100"/></heap><heap nr="1"/><total type="fast" size="20"/><total type="rest" size="100"/><total type="mmap" size="40"/><system type="current" size="200"/></malloc>'
        self.assertEqual(m.parse_heap(data),dict(arenas=2,free_chunk_bytes=120,system_current_bytes=200,mmap_bytes=40))
        for bad in ('<malloc/>',data.replace('size="200"','size="1"'),data.replace('size="20"','size="-1"')):
            with self.assertRaises(ValueError):m.parse_heap(bad)

    def test_bad_or_missing_reclamation_and_live_state_rejected(self):
        for key,value in [('allocated',11),('pinned_active',3),('pid',2),('gc_enabled',False),('workspace_locked',False),
                          ('retained_program_owners',0),('retained_identity_sha256','changed'),('runner_sha256','bad'),
                          ('gc_sha256','bad'),('result',0),('trim_result',0),('utc_ns',0)]:
            a,b=record('before'),record('after');b[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):proof([a,b])
        for rows in ([],[record('before')],[record('after'),record('before')]):
            with self.assertRaises(ValueError):proof(rows)
        with self.assertRaises(ValueError):proof([record('before'),record('after')],prefix='')

    def test_physical_gain_floor_and_free_heap_are_separate_gates(self):
        for change in ('gain','floor','free','rss'):
            a,b=record('before'),record('after')
            if change=='gain':b['host']=copy.deepcopy(a['host'])
            if change=='floor':a['host']['MemAvailable']=2*1024**3-1
            if change=='free':a['heap']['free_chunk_bytes']=1
            if change=='rss':b['process']['RssAnon']=-1
            with self.subTest(change=change),self.assertRaises(ValueError):proof([a,b])


if __name__=='__main__':unittest.main()
