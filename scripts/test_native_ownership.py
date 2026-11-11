"""Aliasing, lazy-load traps, strict bounds and terminal ordering contracts."""
import ast
import base64
import copy
from contextvars import ContextVar
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
import weakref

ROOT=Path(__file__).resolve().parents[1]


def load(name):
    spec=importlib.util.spec_from_file_location('native_test_'+name,ROOT/f'mods/native-ownership/{name}.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


M=load('metadata')


def fixture():
    classes={type(name,(),{}):name for name in (*M.PLAN_CLASSES,*M.BASE_CLASSES,'CudaDialectJitCompiledFunction','CudaDialectJitModule','CompiledKernel')}
    byname={name:cls for cls,name in classes.items()};classes[types.FunctionType]='function'
    def new(label,**fields):
        obj=byname[label]();obj.__dict__.update(fields);return obj
    key=new('ProgramKey',dialect='cute',key='a'*64,name='fixture')
    engine=object()
    def program():
        executable=new('CudaDialectJitCompiledFunction',engine=engine,prefix='b12x_cute_'+'a'*64,
            load_from_binary=True,ir_module=None,artifacts=None,jit_module=None,_default_executor=None)
        return new('CompiledCuTeProgram',__b12x_programs__=(key,),_executable=executable)
    a,b=program(),program()
    scope=new('_RetainedPrograms',owners={id(a):a,id(b):b},cache={'alias':a})
    plan={'_LIVE_RETAINED_PROGRAMS':weakref.WeakSet((scope,))}
    for name,value in (('_RETAINED_PROGRAMS',None),('_PLANNING',None),('_OBSERVERS',()),('_COMPILE_ONLY_LAUNCHES',False)):
        plan[name]=ContextVar(name,default=value)
    return plan,classes,scope,a,b,new,key


def memory(utc=20):
    return dict(pid=1,ppid=2,utc_ns=utc,device_index=0,fraction=1.,allocated=10,reserved=20,cuda_free=100,cuda_total=200,
        pinned={'allocated_bytes.current':1024**2,'active_bytes.current':1024**2,'num_host_alloc':2,'num_host_free':1},
        processes=[dict(pid=p,VmRSS=100,RssAnon=80,pss={'Pss':100,'Pss_Anon':80,'Pss_File':20,'Pss_Shmem':0}) for p in (1,2)],
        process_coverage='self-parent',host={'MemAvailable':20*1024**3,'MemFree':20*1024**3},gc_enabled=True,frozen_objects=0)


class Terminal(BaseException):pass


class Collector(unittest.TestCase):
    def test_distinct_keys_executables_and_shared_engine(self):
        p,c,s,a,b,_,_=fixture();before=(dict(s.owners),dict(s.cache))
        r=M.collect(p,c)
        self.assertTrue(r['complete']);self.assertEqual(len(r['programs']),1)
        self.assertEqual(r['counts']['CompiledCuTeProgram'],2)
        self.assertEqual(r['counts']['CudaDialectJitCompiledFunction'],2)
        self.assertEqual(r['counts']['engine'],1)
        self.assertEqual([e['field'] for e in r['edges']].count('owners'),2)
        self.assertEqual([e['field'] for e in r['edges']].count('cache'),1)
        self.assertEqual(before,(s.owners,s.cache));self.assertFalse(r['engine_identity_is_native_bytes'])

    def test_unknown_subclass_never_invokes_dynamic_access(self):
        p,c,s,a,b,new,key=fixture()
        class Trap:
            def __getattribute__(self,name):raise AssertionError('dynamic access')
        trap=Trap();s.cache['trap']=trap
        r=M.collect(p,c);self.assertFalse(r['complete']);self.assertEqual(r['counts']['UNKNOWN'],1)

    def test_unresolved_carrier_is_not_resolved(self):
        p,c,s,a,b,new,key=fixture()
        deferred=new('DeferredCuTeKernel',__b12x_programs__=(key,),_resolved=None)
        s.owners[id(deferred)]=deferred
        r=M.collect(p,c);self.assertTrue(r['complete'])
        self.assertTrue(next(n for n in r['nodes'] if n['kind']=='DeferredCuTeKernel')['unresolved'])

    def test_explicit_function_dependencies_cycle_and_alias(self):
        p,c,s,a,b,_,key=fixture()
        def function():raise AssertionError('must not execute')
        function.__b12x_programs__=(key,);function.__b12x_dependencies__=(function,a)
        s.cache['function']=function
        r=M.collect(p,c);self.assertTrue(r['complete']);self.assertEqual(r['counts']['function'],1)

    def test_unannotated_function_invalidates_coverage(self):
        p,c,s,*_=fixture();s.cache['function']=lambda:None
        self.assertFalse(M.collect(p,c)['complete'])

    def test_payload_aliases_count_bytes_once_without_contents(self):
        p,c,s,a,b,new,key=fixture();blob=b'private-compiler-payload'
        artifacts=new('JitFunctionArtifacts',PTX=None,CUBIN=blob,SASS=None,MLIR=None)
        a._executable.artifacts=b._executable.artifacts=artifacts
        r=M.collect(p,c);self.assertTrue(r['complete'])
        self.assertEqual(r['counts']['unique_payload_bytes'],len(blob))
        self.assertNotIn(blob.decode(),json.dumps(r))

    def test_materialized_module_and_executor_alias(self):
        p,c,s,a,b,new,key=fixture();engine=a._executable.engine
        module=new('CudaDialectJitModule',engine=engine,_unloaded=False,cuda_library=[object()])
        executor=new('JitExecutor',jit_module=module)
        a._executable.jit_module=module;a._executable._default_executor=executor
        r=M.collect(p,c);self.assertTrue(r['complete']);self.assertEqual(r['counts']['engine'],1)

    def test_bad_metadata_and_program_identity_fail(self):
        for field,value in (('load_from_binary','true'),('prefix',object())):
            p,c,s,a,*_=fixture();vars(a._executable)[field]=value
            self.assertFalse(M.collect(p,c)['complete'])
        p,c,s,a,b,new,key=fixture();key.key='bad';self.assertFalse(M.collect(p,c)['complete'])

    def test_context_must_be_inactive(self):
        for name in ('_RETAINED_PROGRAMS','_PLANNING','_OBSERVERS','_COMPILE_ONLY_LAUNCHES'):
            p,c,s,*_=fixture();p[name].set(True)
            with self.subTest(name=name),self.assertRaises(ValueError):M.collect(p,c)

    def test_roots_edges_nodes_depth_time_and_output_bounds(self):
        for name,value in (('roots',0),('edges',0),('nodes',1),('depth',0),('seconds',0),('output_bytes',32)):
            p,c,s,*_=fixture();limits=dict(M.LIMITS,**{name:value})
            try:r=M.collect(p,c,limits)
            except ValueError:continue
            with self.subTest(name=name):self.assertFalse(r['complete'])

    def test_roots_change_invalidates_inventory(self):
        p,c,s,*_=fixture();real=M.roots;calls=[]
        def changing(*args):
            rows,digest=real(*args);calls.append(1)
            return rows,digest if len(calls)==1 else 'changed'
        with patch.object(M,'roots',side_effect=changing):r=M.collect(p,c)
        self.assertFalse(r['complete'])

    def test_missing_provider_is_not_imported(self):
        with patch.dict(sys.modules,{'b12x._lib.compile_plan':None}),self.assertRaisesRegex(ValueError,'already loaded'):
            M.providers()

    def test_weak_scope_not_retained_after_snapshot(self):
        p,c,s,*_=fixture();reference=weakref.ref(s);M.collect(p,c)
        del s;self.assertIsNone(reference())


class Integration(unittest.TestCase):
    def execute(self, *, missing=None, admission=17*1024**3, original_failure=False, change=None):
        events=[];rows=[];p,c,s,*_=fixture()
        fake=types.SimpleNamespace(collect=lambda *a:events.append('collect') or M.collect(p,c),providers=lambda:(p,c),PROVIDERS=M.PROVIDERS)
        with patch.dict(sys.modules,{'vllm.v1.worker._b12x_native_metadata':fake}):module=load('observe')
        worker=types.SimpleNamespace(device=types.SimpleNamespace(type='cuda',index=None),cache_config=types.SimpleNamespace(kv_cache_memory_bytes=17*1024**3),
            _b12x_startup_coordinator=None,_b12x_stage=None,_b12x_profile_batch=None,_b12x_tuning_cache=False,_b12x_pinned_return_done=True)
        if missing:del vars(worker)[missing]
        def original(w):
            events.append('original-pinned-completed')
            if original_failure:raise ValueError('pinned failed')
            return admission
        cuda=types.SimpleNamespace(is_initialized=lambda:True,current_device=lambda:0,is_current_stream_capturing=lambda:False,
            memory=types.SimpleNamespace(get_allocator_backend=lambda:'native',get_per_process_memory_fraction=lambda d:1.))
        platform=types.SimpleNamespace(current_platform=types.SimpleNamespace(is_integrated_gpu=lambda d:True))
        before,after=memory(),memory(21)
        if change:change(before,after)
        with patch.dict(sys.modules,{'torch':types.SimpleNamespace(cuda=cuda),'vllm.platforms':platform}),patch.object(module,'PINNED_SHA',hashlib.sha256(b'x').hexdigest()),patch.object(Path,'read_bytes',return_value=b'x'),patch.object(module,'snapshot',side_effect=[before,after]),patch.object(module,'emit',side_effect=lambda marker,row:rows.append((marker,row))),patch.object(module,'terminal_hold',side_effect=Terminal):
            wrapped=module.observe_native_owners_terminal(original)
            try:wrapped(worker)
            except Terminal:pass
            with self.assertRaisesRegex(RuntimeError,'startup-once'):wrapped(worker)
        return events,rows

    def test_pinned_then_inventory_then_primary_last_never_returns(self):
        events,rows=self.execute();self.assertEqual(events,['original-pinned-completed','collect'])
        self.assertEqual(rows[-1][0],'B12X_HOST_OWNERSHIP ')
        encoded=''.join(r['data'] for marker,r in rows[:-1]);raw=base64.b64decode(encoded)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),rows[-1][1]['inventory_sha256'])
        self.assertTrue(json.loads(raw)['complete'])

    def test_missing_state_and_pinned_failure_stop_before_collection(self):
        for name in ('_b12x_stage','_b12x_startup_coordinator','_b12x_profile_batch','_b12x_tuning_cache','_b12x_pinned_return_done'):
            with self.subTest(name=name),self.assertRaisesRegex(RuntimeError,'profile preparation'):self.execute(missing=name)
        with self.assertRaisesRegex(ValueError,'pinned failed'):self.execute(original_failure=True)
        for value in (True,0,17*1024**3+1):
            with self.assertRaisesRegex(RuntimeError,'admission'):self.execute(admission=value)

    def test_floor_live_state_and_overhead_are_enforced(self):
        for change in (lambda a,b:a['host'].update(MemAvailable=9*1024**3),lambda a,b:b.update(allocated=11),
                       lambda a,b:b['processes'][0].update(RssAnon=65*1024**2)):
            with self.assertRaises(RuntimeError):self.execute(change=change)

    def test_installer_is_outer_and_preserves_input_ast(self):
        module=load('install');path=Path('/tmp/b12x-pinned-gpu-worker.py')
        if not path.exists():self.skipTest('requires extracted pinned image worker for AST proof')
        source=path.read_text()
        spec=importlib.util.spec_from_file_location('native_pinned_installer',ROOT/'mods/startup-pinned/install.py')
        pinned=importlib.util.module_from_spec(spec);spec.loader.exec_module(pinned)
        original=pinned.transform(source);changed=module.transform(original)
        restored=changed.replace('from vllm.v1.worker._b12x_native_ownership import observe_native_owners_terminal\n\n','').replace('    @observe_native_owners_terminal\n','')
        self.assertEqual(ast.dump(ast.parse(original)),ast.dump(ast.parse(restored)))
        self.assertIn('@observe_native_owners_terminal\n    @release_after_explicit_profile',changed)
        self.assertEqual(hashlib.sha256(original.encode()).hexdigest(),module.SOURCE_SHA256)


class Receipts(unittest.TestCase):
    def fixture_log(self):
        from test_pinned_cache import record
        import native_ownership_receipt as V
        p,c,s,*_=fixture();report=M.collect(p,c);row=memory(21)
        row.update(version=1,boundary=V.BOUNDARY,result=17*1024**3,before=memory(20),
            worker_sha256='w',helper_sha256='h',metadata_sha256='m',providers=M.PROVIDERS,
            pinned_helper_sha256=V.PINNED_SHA,profile_completed=True,inventory_complete=True)
        raw=json.dumps(report,separators=(',',':')).encode();sha=hashlib.sha256(raw).hexdigest()
        encoded=base64.b64encode(raw).decode();parts=[encoded[i:i+3000] for i in range(0,len(encoded),3000)]
        row.update(inventory_sha256=sha,inventory_chunks=len(parts))
        lines=[]
        for phase in ('before','after'):
            pin=record(phase);pin['helper_sha256']=V.PINNED_SHA
            lines.append('B12X_PINNED_RETURN '+json.dumps(pin))
        lines += [V.MARKER+json.dumps(dict(pid=1,index=i,count=len(parts),sha256=sha,data=part)) for i,part in enumerate(parts)]
        lines.append('B12X_HOST_OWNERSHIP '+json.dumps(row))
        return V,lines,dict(pid=1,records=[dict(utc_ns=1)])

    def test_complete_chunks_and_common_pinned_proof_validate(self):
        v,lines,trace=self.fixture_log();r=v.validate('\n'.join(lines),'w','h','m',trace)
        self.assertFalse(r['serving_qualified']);self.assertFalse(r['native_bytes_attributed'])
        self.assertEqual(r['inventory']['counts']['engine'],1)

    def test_missing_corrupt_reordered_duplicate_chunks_fail(self):
        for mode in ('missing','corrupt','after-primary','duplicate'):
            v,lines,trace=self.fixture_log();index=next(i for i,s in enumerate(lines) if v.MARKER in s)
            if mode=='missing':lines.pop(index)
            elif mode=='corrupt':
                chunk=json.loads(lines[index].split(v.MARKER)[1]);chunk['data']='!!!!';lines[index]=v.MARKER+json.dumps(chunk)
            elif mode=='after-primary':lines.append(lines.pop(index))
            else:lines.insert(index,lines[index])
            with self.subTest(mode=mode),self.assertRaises(ValueError):v.validate('\n'.join(lines),'w','h','m',trace)

    def test_bad_sources_state_floor_and_pinned_evidence_fail(self):
        for key,value in (('providers',{}),('inventory_complete',False),('metadata_sha256','wrong'),
                          ('profile_completed',False),('fraction',True),('result',True)):
            v,lines,trace=self.fixture_log();row=json.loads(lines[-1].split('B12X_HOST_OWNERSHIP ')[1]);row[key]=value
            lines[-1]='B12X_HOST_OWNERSHIP '+json.dumps(row)
            with self.subTest(key=key),self.assertRaises(ValueError):v.validate('\n'.join(lines),'w','h','m',trace)
        v,lines,trace=self.fixture_log()
        with self.assertRaises(ValueError):v.validate('\n'.join(lines[1:]),'w','h','m',trace)


if __name__=='__main__':unittest.main()
