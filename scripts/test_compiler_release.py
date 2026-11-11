"""Lookup retirement preserves live owners and must return enough real memory."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
from compiler_release_receipt import validate,MARKER,COMPILER_SHA,PLAN_SHA

ROOT=Path(__file__).resolve().parent.parent


def load():
    spec=importlib.util.spec_from_file_location('release',ROOT/'mods/compiler-cache-release/release.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def row(phase):
    return dict(version=1,phase=phase,boundary='post-explicit-profile',pid=1,utc_ns=1,
        device_index=0,result=17*1024**3,fraction=1.,allocated=10,reserved=20,pinned_owned=3,pinned_active=2,
        process={'RssAnon':(3 if phase=='before' else 1)*1024**3},host={'MemAvailable':8*1024**3},
        worker_sha256='w',helper_sha256='h')


class CompilerRelease(unittest.TestCase):
    def execute(self,*,changed_identity=False,drop=True,active=False):
        module=load();events=[];writes=[];cache=[2]
        def clear():events.append('clear');cache[0]=0
        def trim(pad):self.assertEqual(pad,0);events.append('trim');return 1
        compiler=types.SimpleNamespace(clear_compile_cache=clear,compile_cache_info=lambda:dict(memory_cache_size=cache[0],spec_memo_size=cache[0]))
        plan=types.SimpleNamespace(_RETAINED_PROGRAMS=types.SimpleNamespace(get=lambda:object() if active else None))
        source=dict(compiler_sha256=COMPILER_SHA,plan_sha256=PLAN_SHA,compiler_provider='/pinned/compiler.py')
        identities=[dict(retained_program_owners=1,retained_identity_sha256='stable'),dict(retained_program_owners=1,retained_identity_sha256='changed' if changed_identity else 'stable')]
        before,after=row('before'),row('after')
        if not drop:after['process']['RssAnon']=before['process']['RssAnon']
        cuda=types.SimpleNamespace(is_initialized=lambda:True,current_device=lambda:0,is_current_stream_capturing=lambda:False,
             memory=types.SimpleNamespace(get_allocator_backend=lambda:'native',get_per_process_memory_fraction=lambda d:1.))
        platform=types.SimpleNamespace(current_platform=types.SimpleNamespace(is_integrated_gpu=lambda d:True))
        worker=types.SimpleNamespace(device=types.SimpleNamespace(type='cuda',index=None),cache_config=types.SimpleNamespace(kv_cache_memory_bytes=17*1024**3))
        def original(owner):events.append('original');return 17*1024**3
        with patch.dict(sys.modules,{'torch':types.SimpleNamespace(cuda=cuda),'vllm.platforms':platform}),patch.object(module,'providers',return_value=(compiler,plan,source)),patch.object(module,'retention',side_effect=identities),patch.object(module.ctypes,'CDLL',return_value=types.SimpleNamespace(malloc_trim=trim)),patch.object(module,'snapshot',side_effect=[before,after]),patch.object(module,'emit',side_effect=lambda r:writes.append(r)):
            return module.release_after_explicit_profile(original)(worker),events,writes

    def test_clear_once_before_common_trim_and_preserve_admission(self):
        result,events,rows=self.execute();self.assertEqual(result,17*1024**3);self.assertEqual(events,['original','clear','trim'])
        proof=validate(''.join(MARKER+json.dumps(r)+'\n' for r in rows),'w','h',1)
        self.assertEqual(proof['reclaimed_anon_bytes'],2*1024**3)

    def test_retained_identity_change_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'live ownership'):self.execute(changed_identity=True)

    def test_small_reclamation_refuses_kv(self):
        with self.assertRaisesRegex(RuntimeError,'refuse KV allocation'):self.execute(drop=False)

    def test_active_preparation_rejected_before_eviction(self):
        with self.assertRaisesRegex(RuntimeError,'active preparation'):self.execute(active=True)

    def test_repeated_startup_release_refused_before_original(self):
        module=load()
        with self.assertRaisesRegex(RuntimeError,'startup-once'):
            module.release_after_explicit_profile(lambda w:self.fail('original called'))(types.SimpleNamespace(_b12x_compiler_release_seen=True))

    def test_provider_source_must_match_pinned_bytes(self):
        module=load()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp,'compiler.py');path.write_text('wrong')
            with patch.object(module.importlib,'import_module',return_value=types.SimpleNamespace(__file__=str(path))),self.assertRaisesRegex(RuntimeError,'pinned source'):module.providers()

    def test_wrong_cache_and_identity_receipts_rejected(self):
        _,_,rows=self.execute()
        for key,value in [('retained_identity_sha256','wrong'),('compiler_sha256','wrong'),('allocated',11),('cache',{'memory_cache_size':1,'spec_memo_size':0})]:
            after=dict(rows[1]);after[key]=value
            with self.assertRaises(ValueError):validate(''.join(MARKER+json.dumps(r)+'\n' for r in (rows[0],after)),'w','h',1)


if __name__=='__main__':unittest.main()
