"""CPU contract tests for a scoped allocator cap, not its GPU effectiveness."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from startup_bound_receipt import validate, MARKER
from startup_trace_receipt import safety

ROOT=Path(__file__).resolve().parent.parent


def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/f'mods/startup-bound/{name}.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


class StartupBound(unittest.TestCase):
    def test_restore_after_return_and_exception(self):
        for fail in (False,True):
            module=load('bound'); current=[1.0]; mutations=[]; writes=[]
            def set_fraction(value,device): mutations.append(value);current[0]=value
            memory=types.SimpleNamespace(get_allocator_backend=lambda:'native',
                get_per_process_memory_fraction=lambda d:current[0],
                set_per_process_memory_fraction=set_fraction,
                memory_reserved=lambda d:700,memory_allocated=lambda d:600)
            torch=types.SimpleNamespace(cuda=types.SimpleNamespace(memory=memory,
                is_initialized=lambda:True,get_device_properties=lambda d:types.SimpleNamespace(total_memory=1000)))
            platform=types.SimpleNamespace(current_platform=types.SimpleNamespace(is_integrated_gpu=lambda d:True))
            device=types.SimpleNamespace(type='cuda',index=0)
            with tempfile.TemporaryDirectory() as tmp:
                Path(tmp,'utils.py').write_text('# loader\n');Path(tmp,'bound.py').write_text('# helper\n')
                def original(model,config,target):
                    self.assertEqual(current[0],.8)
                    if fail: raise RuntimeError('original error')
                    return model
                with patch.dict(sys.modules,{'torch':torch,'vllm.platforms':platform}), patch.object(module,'__file__',str(Path(tmp,'bound.py'))), patch.object(module.os,'write',side_effect=lambda fd,data:writes.append(data.decode())):
                    if fail:
                        with self.assertRaisesRegex(RuntimeError,'original error'):module.bounded_postload(original)('sentinel',None,device)
                    else:self.assertEqual(module.bounded_postload(original)('sentinel',None,device),'sentinel')
                self.assertEqual(mutations,[.8,1.0]);self.assertEqual(current[0],1.0)
                events=[json.loads(line.split(MARKER,1)[1]) for line in writes]
                self.assertEqual([e['event'] for e in events],['enter','exit'])
                self.assertEqual(events[-1]['success'],not fail)
                if not fail:
                    # Two sequential successful scopes represent target and MTP.
                    second=[dict(e,scope=2) for e in events]
                    log=''.join(MARKER+json.dumps(e)+'\n' for e in events+second)
                    result=validate(log,events[0]['loader_sha256'],events[0]['bound_sha256'],events[0]['pid'])
                    self.assertEqual(result['scopes'],2)
                    with self.assertRaises(ValueError):validate(log.replace('"fraction": 1.0','"fraction": 0.8'),events[0]['loader_sha256'],events[0]['bound_sha256'],events[0]['pid'])

    def test_wrong_backend_fraction_or_oversized_entry_fails_without_body(self):
        for setting in ('backend','fraction','reserved','device'):
            module=load('bound');calls=[]
            memory=types.SimpleNamespace(get_allocator_backend=lambda:'cudaMallocAsync' if setting=='backend' else 'native',
                get_per_process_memory_fraction=lambda d:.9 if setting=='fraction' else 1.0,
                memory_reserved=lambda d:900 if setting=='reserved' else 700,
                set_per_process_memory_fraction=lambda *a:calls.append(a))
            torch=types.SimpleNamespace(cuda=types.SimpleNamespace(memory=memory,is_initialized=lambda:True,
                get_device_properties=lambda d:types.SimpleNamespace(total_memory=1000)))
            platform=types.SimpleNamespace(current_platform=types.SimpleNamespace(is_integrated_gpu=lambda d:True))
            device=types.SimpleNamespace(type='cpu' if setting=='device' else 'cuda',index=0)
            with patch.dict(sys.modules,{'torch':torch,'vllm.platforms':platform}),self.assertRaises(RuntimeError):
                module.bounded_postload(lambda *a:self.fail('body ran'))(None,None,device)
            self.assertEqual(calls,[])

    def test_wrong_loader_cannot_be_patched(self):
        installer=load('install')
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp,'utils.py');p.write_text('wrong source')
            with self.assertRaises(ValueError):installer.install(p)
            self.assertEqual(p.read_text(),'wrong source')
            self.assertFalse(p.with_name('_b12x_startup_bound.py').exists())

    def test_safety_reads_completed_lines_and_retains_short_dip(self):
        safe='B12X_STARTUP_MEMORY '+json.dumps({'host':{'MemAvailable':3*1024**3}})+'\n'
        low='B12X_STARTUP_MEMORY '+json.dumps({'host':{'MemAvailable':2*1024**3-1}})+'\n'
        safety(safe+'B12X_STARTUP_MEMORY {')
        with self.assertRaises(ValueError):safety(safe+low+safe)

    def test_missing_or_wrong_scope_evidence_fails(self):
        with self.assertRaises(ValueError):validate('', 'loader','helper',1)
        event=dict(event='enter',scope=1,pid=1,previous=1.,requested=.8,capacity=1000,limit=800,
            allocated=600,reserved=700,loader_sha256='loader',bound_sha256='helper',fraction=.8,success=False,backend='native')
        events=[event,dict(event,event='exit',fraction=1.,success=True),dict(event,scope=2),dict(event,event='exit',scope=2,fraction=1.,success=True)]
        for field,value in (('pid',2),('scope',3),('bound_sha256','wrong'),('success',False)):
            wrong=[dict(e) for e in events];wrong[-1][field]=value
            with self.assertRaises(ValueError):validate(''.join(MARKER+json.dumps(e)+'\n' for e in wrong),'loader','helper',1)

    def test_candidate_adds_only_allocator_mod(self):
        original=(ROOT/'recipes/observations/startup-memory.yaml').read_text()
        bounded=(ROOT/'recipes/observations/startup-bound.yaml').read_text()
        self.assertEqual(original.replace('  - /home/nvidia/b12x/mods/startup-memory\n','  - /home/nvidia/b12x/mods/startup-memory\n  - /home/nvidia/b12x/mods/startup-bound\n'),bounded)


if __name__=='__main__':unittest.main()
