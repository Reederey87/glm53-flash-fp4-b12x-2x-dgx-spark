"""Content-free, deduplicated metadata and a terminal collection boundary."""
import importlib.util
import io
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch, mock_open
from compiler_ownership_receipt import validate

ROOT=Path(__file__).resolve().parent.parent


def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/f'mods/compiler-ownership/{name}.py')
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def memory():
    return dict(version=1,boundary='post-explicit-profile',pid=1,ppid=0,utc_ns=1,device_index=0,
        fraction=1.,allocated=10,reserved=20,cuda_free=30,cuda_total=40,
        pinned={'allocated_bytes.current':10,'active_bytes.current':5,'num_host_alloc':1,'num_host_free':0},
        host={'MemAvailable':16*1024**3},processes=[{'pid':1,'VmRSS':1024**3}],
        result=17*1024**3,worker_sha256='w',helper_sha256='h',metadata_sha256='m')


class CompilerOwnership(unittest.TestCase):
    def test_deduplicates_payloads_without_content_or_extension_sizeof(self):
        module=load('metadata')
        def forbidden(self): raise AssertionError('extension sizeof invoked')
        kind=type('CompiledFxGraph',(),{'__module__':'torch._inductor.output_code','__sizeof__':forbidden})
        blob=b'PRIVATE-CONTENT'*1000; first=kind(); second=kind()
        first.source_code=blob; second.source_code=blob; first.constants={'hidden':blob*2}
        result=module.compiler_summary([first,second,type('Odd',(),{'__module__':None})()])
        self.assertEqual(result['unique_payload_bytes'],sys.getsizeof(blob))
        self.assertEqual(result['unique_payload_objects'],1)
        self.assertNotIn('PRIVATE-CONTENT',json.dumps(result))
        self.assertEqual(sum(result['target_counts'].values()),2)

    def test_metadata_bounds_are_reported(self):
        module=load('metadata'); kind=type('CompiledFxGraph',(),{'__module__':'torch._inductor.output_code'})
        value=kind(); value.bundle=[bytes([i])*100 for i in range(20)]
        self.assertTrue(module.compiler_summary([value],max_nodes=2)['truncated'])
        self.assertGreater(module.compiler_summary([value],max_depth=0)['depth_omissions'],0)
        self.assertTrue(module.compiler_summary([value,value],max_gc_objects=1)['truncated'])

    def test_mapping_summary_has_no_addresses_or_paths(self):
        module=load('metadata')
        source='001000-002000 rw-p 0000 00:00 0 [heap]\nRss: 12 kB\nPss: 10 kB\nAnonymous: 8 kB\n003000-004000 r-xp 0000 01:01 2 /private/secret.so\nRss: 4 kB\n'
        result=module.mapping_summary(io.StringIO(source))
        self.assertEqual(result['buckets']['heap']['Rss'],12*1024)
        self.assertNotIn('secret',json.dumps(result)); self.assertNotIn('001000',json.dumps(result))
        self.assertTrue(module.mapping_summary(io.StringIO(source),max_maps=1)['truncated'])

    def test_three_records_validate_and_bad_evidence_fails(self):
        module=load('metadata'); row=memory()
        common={k:row[k] for k in ('version','boundary','pid','utc_ns','worker_sha256','helper_sha256','metadata_sha256')}
        objects=dict(common,objects=module.compiler_summary([])); maps=dict(common,mappings=module.mapping_summary(io.StringIO('1000-2000 rw-p 0000 00:00 0 [heap]\nRss: 1 kB\n')))
        lines=['B12X_COMPILER_OBJECTS '+json.dumps(objects),'B12X_COMPILER_MAPS '+json.dumps(maps),'B12X_HOST_OWNERSHIP '+json.dumps(row)]
        self.assertFalse(validate('\n'.join(lines),'w','h','m',1)['serving_qualified'])
        with self.assertRaises(ValueError): validate('\n'.join(lines),'w','h','wrong',1)
        with self.assertRaises(ValueError): validate('\n'.join(lines[1:]),'w','h','m',1)
        maps['pid']=2; lines[1]='B12X_COMPILER_MAPS '+json.dumps(maps)
        with self.assertRaises(ValueError): validate('\n'.join(lines),'w','h','m',1)

    def test_original_profile_then_auxiliary_then_primary_then_terminal(self):
        events=[]; fake=types.SimpleNamespace(compiler_summary=lambda:events.append('objects') or {},mapping_summary=lambda source:events.append('maps') or {})
        with patch.dict(sys.modules,{'vllm.v1.worker._b12x_compiler_metadata':fake}): module=load('observe')
        def original(worker): events.append('original'); return 17*1024**3
        with patch.object(module,'snapshot',side_effect=[memory(),memory()]),patch('builtins.open',mock_open(read_data='')),patch.object(module,'emit',side_effect=lambda marker,row:events.append(marker.strip())),patch.object(module.time,'sleep',side_effect=lambda n:events.append(n)):
            with self.assertRaisesRegex(RuntimeError,'intentional terminal stop'):
                module.observe_compiler_ownership(original)(types.SimpleNamespace(cache_config=types.SimpleNamespace(kv_cache_memory_bytes=17*1024**3)))
        self.assertEqual(events,['original','objects','maps','B12X_COMPILER_OBJECTS','B12X_COMPILER_MAPS','B12X_HOST_OWNERSHIP',120])

    def test_collection_refused_without_extra_headroom(self):
        fake=types.SimpleNamespace(compiler_summary=lambda:None,mapping_summary=lambda source:None)
        with patch.dict(sys.modules,{'vllm.v1.worker._b12x_compiler_metadata':fake}): module=load('observe')
        row=memory(); row['host']['MemAvailable']=6*1024**3
        with patch.object(module,'snapshot',return_value=row),self.assertRaisesRegex(RuntimeError,'requires8GiB'):
            module.observe_compiler_ownership(lambda w:1)(types.SimpleNamespace(cache_config=types.SimpleNamespace(kv_cache_memory_bytes=17*1024**3)))


if __name__=='__main__':unittest.main()
