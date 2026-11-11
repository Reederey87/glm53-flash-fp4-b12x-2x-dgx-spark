"""One-shot heap trim must preserve admission and reject insufficient return."""
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from host_trim_receipt import validate, MARKER

ROOT = Path(__file__).resolve().parent.parent


def load():
    spec = importlib.util.spec_from_file_location('trim', ROOT/'mods/explicit-kv-host-trim/trim.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def record(phase):
    return dict(version=1, phase=phase, boundary='post-explicit-profile', pid=1, utc_ns=1,
                device_index=0, result=17*1024**3-2048, fraction=1., allocated=10, reserved=20,
                pinned_owned=5, pinned_active=2, worker_sha256='w', helper_sha256='h',
                process=dict(RssAnon=(3 if phase=='before' else 1)*1024**3),
                host=dict(MemAvailable=8*1024**3))


class HostTrim(unittest.TestCase):
    def execute(self, *, fraction=1., capture=False, drop=True, request=17*1024**3, original_failure=False):
        module = load(); events = []; writes = []
        def original(worker):
            events.append('original')
            if original_failure: raise RuntimeError('original failure')
            return 17*1024**3-2048
        def trim(pad): self.assertEqual(pad, 0); events.append('trim'); return 1
        cuda = types.SimpleNamespace(is_initialized=lambda:True, current_device=lambda:0,
            is_current_stream_capturing=lambda:capture,
            memory=types.SimpleNamespace(get_allocator_backend=lambda:'native',get_per_process_memory_fraction=lambda d:fraction))
        platform = types.SimpleNamespace(current_platform=types.SimpleNamespace(is_integrated_gpu=lambda d:True))
        before, after = record('before'), record('after')
        if not drop: after['process']['RssAnon'] = before['process']['RssAnon']
        worker = types.SimpleNamespace(cache_config=types.SimpleNamespace(kv_cache_memory_bytes=request),
                                       device=types.SimpleNamespace(type='cuda',index=None))
        with patch.dict(sys.modules, {'torch':types.SimpleNamespace(cuda=cuda),'vllm.platforms':platform}), patch.object(module.ctypes,'CDLL',return_value=types.SimpleNamespace(malloc_trim=trim)), patch.object(module,'snapshot',side_effect=[before,after]), patch.object(module,'emit',side_effect=lambda row:writes.append(row)):
            return module.trim_after_explicit_profile(original)(worker), events, writes

    def test_preserves_original_admission_and_one_trim(self):
        result, events, rows = self.execute()
        self.assertEqual(result,17*1024**3-2048); self.assertEqual(events,['original','trim'])
        log=''.join(MARKER+json.dumps(row)+'\n' for row in rows)
        self.assertEqual(validate(log,'w','h',1)['reclaimed_anon_bytes'],2*1024**3)

    def test_wrong_request_rejected_before_profiling(self):
        with self.assertRaisesRegex(RuntimeError,'frozen explicit17G'): self.execute(request=None)

    def test_original_failure_never_reaches_trim(self):
        with self.assertRaisesRegex(RuntimeError,'original failure'): self.execute(original_failure=True)

    def test_unsafe_cuda_state_refused(self):
        for options in ({'fraction':.8},{'capture':True}):
            with self.assertRaisesRegex(RuntimeError,'restored fraction'): self.execute(**options)

    def test_insufficient_return_blocks_kv(self):
        with self.assertRaisesRegex(RuntimeError,'refuse KV allocation'): self.execute(drop=False)

    def test_invalid_proof_prevents_qualification(self):
        before, after = record('before'), record('after'); after.update(trim_result=1,elapsed_ns=1)
        for key, value in [('allocated',11),('pid',2),('helper_sha256','bad'),('trim_result',0),('result',42)]:
            bad=dict(after); bad[key]=value
            with self.assertRaises(ValueError): validate(''.join(MARKER+json.dumps(r)+'\n' for r in (before,bad)),'w','h',1)
        with self.assertRaises(ValueError): validate('','w','h',1)


if __name__ == '__main__': unittest.main()
