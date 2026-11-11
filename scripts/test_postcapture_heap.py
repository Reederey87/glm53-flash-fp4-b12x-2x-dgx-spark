"""Postcapture heap return must preserve captures and reject weak reclamation."""
import copy
import ctypes
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from postcapture_heap_receipt import validate, validate_observation, MARKER, PROVIDERS

ROOT = Path(__file__).resolve().parent.parent


def load():
    sp=importlib.util.spec_from_file_location('heap_return',ROOT/'mods/postcapture-heap/return_heap.py')
    m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m


def record(phase):
    return dict(version=1,phase=phase,boundary='post-capture-before-second-warmup',pid=1,utc_ns=10,
        device_index=0,result=-17,kv_bytes=17*1024**3,fraction=1.,allocated=10,reserved=20,
        pinned_owned=5,pinned_active=2,gc_enabled=True,frozen_objects=0,workspace_locked=True,graphs_captured=True,
        retained_program_owners=1,retained_identity_sha256='a'*64,runner_sha256='r',helper_sha256='h',
        heap=dict(arenas=2,free_chunk_bytes=1024**3,system_current_bytes=2*1024**3,mmap_bytes=0),
        process=dict(RssAnon=(3 if phase=='before' else 1)*1024**3,VmRSS=4*1024**3),
        pss={k:1024 for k in ('Rss','Pss_Anon','Anonymous','Private_Dirty','Shared_Dirty','AnonHugePages','Swap','SwapPss')},
        host=dict(MemAvailable=8*1024**3+(512*1024**2 if phase=='after' else 0)),elapsed_ns=1,trim_result=1,**PROVIDERS)


def proof(rows, prefix='Graph capturing finished\n'):
    return validate(prefix+''.join(MARKER+json.dumps(r)+'\n' for r in rows),'r','h',dict(pid=1,records=[dict(utc_ns=1)]))


class PostcaptureHeap(unittest.TestCase):
    def execute(self, *, request=17*1024**3, capture=False, fraction=1., original_failure=False, free=True, returned=True, locked=True, observation=False, completed=True):
        m=load();self.events=[];rows=[];self.rows=rows
        manager=types.SimpleNamespace(needs_capture=lambda:True,_graphs_captured=False)
        def original(runner):
            self.events.append('capture')
            if original_failure:raise RuntimeError('original failed')
            manager._graphs_captured=completed;return -17
        def trim(pad):self.assertEqual(pad,0);self.events.append('trim');return 1
        cuda=types.SimpleNamespace(is_initialized=lambda:True,current_device=lambda:0,is_current_stream_capturing=lambda:capture,
            memory=types.SimpleNamespace(get_allocator_backend=lambda:'native',get_per_process_memory_fraction=lambda d:fraction))
        platform=types.SimpleNamespace(current_platform=types.SimpleNamespace(is_integrated_gpu=lambda d:True))
        runner=types.SimpleNamespace(device=types.SimpleNamespace(type='cuda',index=None),
            cache_config=types.SimpleNamespace(kv_cache_memory_bytes=request),cudagraph_manager=manager)
        a,b=record('before'),record('after');a['workspace_locked']=b['workspace_locked']=locked
        if not free:a['heap']['free_chunk_bytes']=1
        if not returned:b['process']['RssAnon']=a['process']['RssAnon']
        if observation:a['phase']='observe'
        def hold():self.events.append('hold');raise RuntimeError('held terminally')
        with patch.dict(sys.modules,{'torch':types.SimpleNamespace(cuda=cuda),'vllm.platforms':platform}),patch.object(m,'providers',return_value=(None,None,{})),patch.object(m,'libc_api',return_value=types.SimpleNamespace(malloc_trim=trim)),patch.object(m,'snapshot',side_effect=[a,b]),patch.object(m,'emit',side_effect=rows.append),patch.object(m,'terminal_hold',side_effect=hold):
            wrapped=(m.observe_after_capture if observation else m.return_heap_after_capture)(original);result=wrapped(runner)
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
        with self.assertRaisesRegex(RuntimeError,'did not complete'):self.execute(completed=False)

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

    def test_terminal_observation_never_trims_or_requires_free_chunks(self):
        with self.assertRaisesRegex(RuntimeError,'held terminally'):self.execute(observation=True,free=False)
        self.assertEqual(self.events,['capture','hold']);self.assertEqual(len(self.rows),1)
        text='Graph capturing finished\n'+MARKER+json.dumps(self.rows[0])+'\n'
        out=validate_observation(text,'r','h',dict(pid=1,records=[dict(utc_ns=1)]))
        self.assertFalse(out['cleanup_performed']);self.assertFalse(out['inference_qualified'])
        with self.assertRaises(ValueError):validate_observation(text+text,'r','h',dict(pid=1,records=[dict(utc_ns=1)]))

    def test_fixed_report_buffer_overflow_is_refused_and_closed(self):
        m=load();closed=[]
        api=types.SimpleNamespace(fmemopen=lambda buffer,size,mode:1,malloc_info=lambda a,b:0,
            fflush=lambda stream:-1,ferror=lambda stream:1,fclose=lambda stream:closed.append(stream) or 0)
        with self.assertRaisesRegex(RuntimeError,'exceeded fixed'):m.heap_info(api)
        self.assertEqual(closed,[1])

    def test_fixed_report_buffer_native_contract_and_bound(self):
        m=load();closed=[];size=[]
        data=b'<malloc version="1"><heap nr="0"/><total type="fast" size="0"/><total type="rest" size="1"/><total type="mmap" size="2"/><system type="current" size="3"/></malloc>'
        def open_stream(buffer,length,mode):
            self.assertEqual(length,128*1024);self.assertEqual(mode,b'w')
            ctypes.memmove(buffer,data,len(data));size.append(length);return 1
        api=types.SimpleNamespace(fmemopen=open_stream,malloc_info=lambda a,b:0,fflush=lambda s:0,ferror=lambda s:0,
            ftell=lambda s:len(data),fclose=lambda s:closed.append(s) or 0)
        self.assertEqual(m.heap_info(api)['free_chunk_bytes'],1);self.assertEqual(closed,[1])
        api.ftell=lambda s:128*1024
        with self.assertRaisesRegex(RuntimeError,'invalid fixed'):m.heap_info(api)


if __name__=='__main__':unittest.main()
