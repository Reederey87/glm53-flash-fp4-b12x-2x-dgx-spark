"""One native host-cache call must precede KV and prove known idle-byte return."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from pinned_cache_receipt import validate, MARKER, API_SHA256, HEADER_SHA256

ROOT = Path(__file__).resolve().parent.parent


def load():
    spec = importlib.util.spec_from_file_location('pinned_release', ROOT/'mods/startup-pinned/release.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def record(phase):
    return dict(version=1, phase=phase, boundary='post-explicit-profile', pid=1, utc_ns=10,
                device_index=0, result=17*1024**3, fraction=1., allocated=10, reserved=20,
                pinned_owned=1024**2+(512*1024**2 if phase=='before' else 0), pinned_active=1024**2,
                num_host_alloc=2, num_host_free=0 if phase=='before' else 1,
                worker_sha256='w', helper_sha256='h', api_sha256=API_SHA256, header_sha256=HEADER_SHA256,
                host=dict(MemAvailable=8*1024**3+(512*1024**2 if phase=='after' else 0)), elapsed_ns=1)


def proof(rows):
    return validate(''.join(MARKER+json.dumps(r)+'\n' for r in rows), 'w', 'h',
                    dict(pid=1, records=[dict(utc_ns=1)]))


class PinnedCache(unittest.TestCase):
    def execute(self, *, fraction=1., capture=False, request=17*1024**3, original_failure=False, drop=True, coordinator=None):
        module=load(); events=[]; rows=[]
        def original(owner):
            events.append('original')
            if original_failure: raise RuntimeError('original failure')
            return 17*1024**3
        def release(): events.append('host-cache')
        cuda=types.SimpleNamespace(is_initialized=lambda:True,current_device=lambda:0,is_current_stream_capturing=lambda:capture,
            memory=types.SimpleNamespace(get_allocator_backend=lambda:'native',get_per_process_memory_fraction=lambda d:fraction))
        torch=types.SimpleNamespace(cuda=cuda,accelerator=types.SimpleNamespace(memory=types.SimpleNamespace(empty_host_cache=release)))
        platform=types.SimpleNamespace(current_platform=types.SimpleNamespace(is_integrated_gpu=lambda d:True))
        before,after=record('before'),record('after')
        if not drop: after['pinned_owned']=before['pinned_owned']
        worker=types.SimpleNamespace(device=types.SimpleNamespace(type='cuda',index=None),
            cache_config=types.SimpleNamespace(kv_cache_memory_bytes=request),_b12x_startup_coordinator=coordinator)
        with patch.dict(sys.modules,{'torch':torch,'vllm.platforms':platform}), patch.object(module,'provider',return_value={}), patch.object(module,'snapshot',side_effect=[before,after]), patch.object(module,'emit',side_effect=rows.append):
            wrapped=module.release_after_explicit_profile(original)
            result=wrapped(worker)
            with self.assertRaisesRegex(RuntimeError,'startup-once'): wrapped(worker)
        return result,events,rows

    def test_original_result_then_one_public_host_cache_call(self):
        result,events,rows=self.execute()
        self.assertEqual(result,17*1024**3);self.assertEqual(events,['original','host-cache'])
        self.assertEqual(proof(rows)['idle_returned_bytes'],512*1024**2)

    def test_wrong_request_and_original_failure(self):
        with self.assertRaisesRegex(RuntimeError,'frozen explicit17G'):self.execute(request=None)
        with self.assertRaisesRegex(RuntimeError,'original failure'):self.execute(original_failure=True)

    def test_unsafe_boundary_refused(self):
        for options in ({'fraction':.8},{'capture':True},{'coordinator':object()}):
            with self.assertRaises(RuntimeError):self.execute(**options)

    def test_insufficient_idle_return_refuses_kv(self):
        with self.assertRaisesRegex(RuntimeError,'refuse KV allocation'):self.execute(drop=False)

    def test_bad_receipts_and_live_state_rejected(self):
        for key,value in [('allocated',11),('pinned_active',1024**2+1),('pinned_owned',513*1024**2),
                          ('num_host_alloc',3),('num_host_free',0),('pid',2),('api_sha256','bad'),
                          ('header_sha256','bad'),('helper_sha256','bad'),('result',42),('utc_ns',0)]:
            a,b=record('before'),record('after');b[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):proof([a,b])
        for rows in ([],[record('before')],[record('after'),record('before')]):
            with self.assertRaises(ValueError):proof(rows)

    def test_event_retirement_is_not_counted_as_known_idle_return(self):
        a,b=record('before'),record('after')
        a['pinned_active']+=384*1024**2
        with self.assertRaises(ValueError):proof([a,b])
        a['pinned_owned']+=384*1024**2
        self.assertEqual(proof([a,b])['idle_returned_bytes'],512*1024**2)

    def test_physical_gain_required(self):
        a,b=record('before'),record('after');b['host']=copy.deepcopy(a['host'])
        with self.assertRaises(ValueError):proof([a,b])

    def test_provider_is_hash_pinned(self):
        module=load()
        fake=types.SimpleNamespace(__file__=__file__,accelerator=types.SimpleNamespace(memory=types.SimpleNamespace(__file__=__file__)))
        with self.assertRaises((FileNotFoundError,RuntimeError)):module.provider(fake)


if __name__ == '__main__':unittest.main()
