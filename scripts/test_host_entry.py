"""Earlier terminal boundary must never execute the wrapped warmup."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from host_ownership_receipt import validate, MARKER

ROOT = Path(__file__).resolve().parent.parent


class HostEntry(unittest.TestCase):
    def test_original_warmup_never_executes(self):
        spec = importlib.util.spec_from_file_location('entry', ROOT/'mods/host-ownership-entry/observe.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        events = []
        def original(worker): raise AssertionError('warmup executed')
        with patch.object(module, 'snapshot', return_value={'boundary': 'pre-warmup'}), patch.object(module.os, 'write', side_effect=lambda fd, data: events.append('record') or len(data)), patch.object(module.time, 'sleep', side_effect=lambda n: events.append(n)):
            with self.assertRaisesRegex(RuntimeError, 'intentional terminal stop'):
                module.observe_before_warmup(original)(None)
        self.assertEqual(events, ['record', 120])

    def test_wrong_boundary_is_rejected_before_other_proof(self):
        with self.assertRaisesRegex(ValueError, 'wrong ownership observation boundary'):
            validate(MARKER+json.dumps({'boundary': 'post-warmup'}), 'worker', 'helper', 1, 'pre-warmup')


if __name__ == '__main__': unittest.main()
