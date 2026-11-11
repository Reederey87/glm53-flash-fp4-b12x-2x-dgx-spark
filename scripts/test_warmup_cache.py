"""CPU contracts for outer-warmup cleanup and actual-receipt validation."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch,mock_open

from warmup_cache_receipt import validate,MARKER

ROOT=Path(__file__).resolve().parent.parent


def load(name):
    s=importlib.util.spec_from_file_location(name,ROOT/f'mods/warmup-cache-return/{name}.py')
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


class WarmupCache(unittest.TestCase):
    def test_outer_return_preserves_result_and_records_reclamation(self):
        for index in (None,0):
            m=load('release');reserved=[256*1024**2];calls=[];writes=[]
            def clear():calls.append('clear');reserved[0]=64*1024**2
            def original(worker):calls.append('original-return');return 'sentinel'
            cuda=types.SimpleNamespace(is_initialized=lambda:True,current_device=lambda:0,
                is_current_stream_capturing=lambda:False,empty_cache=clear,
                memory=types.SimpleNamespace(get_allocator_backend=lambda:'native',get_per_process_memory_fraction=lambda d:1.),
                memory_allocated=lambda d:32*1024**2,memory_reserved=lambda d:reserved[0])
            platform=types.SimpleNamespace(current_platform=types.SimpleNamespace(is_integrated_gpu=lambda d:True))
            with tempfile.TemporaryDirectory() as tmp:
                Path(tmp,'gpu_worker.py').write_text('#worker');Path(tmp,'release.py').write_text('#helper')
                with patch.object(m,'__file__',str(Path(tmp,'release.py'))),patch.dict(sys.modules,{'torch':types.SimpleNamespace(cuda=cuda),'vllm.platforms':platform}),patch('builtins.open',mock_open(read_data='MemFree: 4194304 kB\nMemAvailable: 6291456 kB\n')),patch.object(m.os,'write',side_effect=lambda fd,data:writes.append(data.decode())):
                    worker=types.SimpleNamespace(device=types.SimpleNamespace(type='cuda',index=index))
                    self.assertEqual(m.return_unused_cuda_cache(original)(worker),'sentinel')
            self.assertEqual(calls,['original-return','clear'])
            rows=[json.loads(x.split(MARKER,1)[1]) for x in writes]
            result=validate(''.join(writes),rows[0]['worker_sha256'],rows[0]['helper_sha256'],rows[0]['pid'],64*1024**2)
            self.assertEqual(result['returned_bytes'],192*1024**2)

    def test_failed_original_never_clears(self):
        m=load('release')
        def fail(worker):raise RuntimeError('original failure')
        with self.assertRaisesRegex(RuntimeError,'original failure'):
            m.return_unused_cuda_cache(fail)(None)

    def test_capture_or_unrestored_fraction_never_clears(self):
        for capture,fraction in ((True,1.),(False,.8)):
            m=load('release');calls=[]
            cuda=types.SimpleNamespace(is_initialized=lambda:True,is_current_stream_capturing=lambda:capture,
                empty_cache=lambda:calls.append('clear'),memory=types.SimpleNamespace(get_allocator_backend=lambda:'native',get_per_process_memory_fraction=lambda d:fraction))
            platform=types.SimpleNamespace(current_platform=types.SimpleNamespace(is_integrated_gpu=lambda d:True))
            with patch.dict(sys.modules,{'torch':types.SimpleNamespace(cuda=cuda),'vllm.platforms':platform}),self.assertRaises(RuntimeError):
                m.return_unused_cuda_cache(lambda w:None)(types.SimpleNamespace(device=types.SimpleNamespace(type='cuda',index=0)))
            self.assertEqual(calls,[])

    def test_wrong_or_incomplete_evidence_rejected(self):
        with self.assertRaises(ValueError):validate('','worker','helper',1)
        before=dict(phase='before',pid=1,worker_sha256='worker',helper_sha256='helper',fraction=1.,allocated=10,reserved=30,device_index=0,utc_ns=1,host=dict(MemAvailable=4*1024**3))
        after=dict(before,phase='after',reserved=20,utc_ns=2)
        for field,value in (('pid',2),('allocated',9),('reserved',31),('fraction',.8),('helper_sha256','wrong')):
            changed=dict(after);changed[field]=value
            with self.assertRaises(ValueError):validate(''.join(MARKER+json.dumps(r)+'\n' for r in (before,changed)),'worker','helper',1)
        with self.assertRaises(ValueError):validate(''.join(MARKER+json.dumps(r)+'\n' for r in (before,after)),'worker','helper',1,11)

    def test_wrong_image_refused_before_mutation(self):
        m=load('install')
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp,'gpu_worker.py');target.write_text('wrong')
            with self.assertRaises(ValueError):m.install(target)
            self.assertEqual(target.read_text(),'wrong')
            self.assertFalse(target.with_name('_b12x_warmup_cache.py').exists())


if __name__=='__main__':unittest.main()
