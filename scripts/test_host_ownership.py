"""Terminal boundary and bounded ownership record contracts."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from host_ownership_receipt import validate, MARKER

ROOT = Path(__file__).resolve().parent.parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/f'mods/host-ownership/{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Ownership(unittest.TestCase):
    def test_terminal_boundary_and_fallback(self):
        module = load('observe'); events = []
        def original(worker): events.append('original-return')
        with patch.object(module, 'snapshot', return_value={'test': 1}), patch.object(module.os, 'write', side_effect=lambda fd, data: events.append('record') or len(data)), patch.object(module.time, 'sleep', side_effect=lambda n: events.append(n)):
            with self.assertRaisesRegex(RuntimeError, 'intentional terminal stop'):
                module.observe_and_hold(original)(None)
        self.assertEqual(events, ['original-return', 'record', 120])

    def test_original_failure_never_records(self):
        module = load('observe')
        def fail(worker): raise RuntimeError('original failure')
        with patch.object(module, 'snapshot') as snapshot, self.assertRaisesRegex(RuntimeError, 'original failure'):
            module.observe_and_hold(fail)(None)
        snapshot.assert_not_called()

    def test_invalid_evidence_rejected(self):
        row = dict(version=1, pid=1, ppid=0, utc_ns=1, device_index=0, fraction=1., allocated=1,
                   reserved=2, cuda_free=3, cuda_total=4, worker_sha256='w', helper_sha256='h',
                   pinned={'allocated_bytes.current': 10, 'active_bytes.current': 8, 'num_host_alloc': 1, 'num_host_free': 0},
                   host={'MemAvailable': 4*1024**3}, processes=[{'pid': 1}])
        log = MARKER + json.dumps(row) + '\n'
        self.assertEqual(validate(log, 'w', 'h', 1)['pinned_inactive_bytes'], 2)
        for key, value in [('pid', 2), ('helper_sha256', 'bad'), ('fraction', .8), ('allocated', 3), ('processes', [])]:
            bad = dict(row); bad[key] = value
            with self.assertRaises(ValueError): validate(MARKER+json.dumps(bad), 'w', 'h', 1)
        with self.assertRaises(ValueError): validate(log+log, 'w', 'h', 1)
        with self.assertRaises(ValueError): validate('', 'w', 'h', 1)

    def test_wrong_source_untouched(self):
        module = load('install')
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp, 'gpu_worker.py'); target.write_text('wrong')
            with self.assertRaises(ValueError): module.install(target)
            self.assertEqual(target.read_text(), 'wrong')


if __name__ == '__main__': unittest.main()
