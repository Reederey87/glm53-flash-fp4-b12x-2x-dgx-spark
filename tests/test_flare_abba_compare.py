import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from flare_abba_compare import ORDER, report


class CounterbalancedReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        receipts = ROOT / 'receipts/flare-qualification-20261115'
        # Historical observations exercise the real validators; fabricated identity
        # metadata below belongs only to this CPU parser test, never a live receipt.
        for step, policy in enumerate(ORDER):
            for workload, source in (('mixed', f'bounded-retry-{policy}-mixed.jsonl'),
                                     ('long-output', f'long-output-eos-{policy}-long-output.jsonl')):
                shutil.copyfile(receipts / source, self.directory / f'{step}-{policy}-{workload}.jsonl')
            for node in ('head', 'worker'):
                prefix = f'{step}-{policy}-{node}'
                invocation = f'cpu-fixture-{node}-{step}'
                (self.directory / f'{prefix}-invocation.txt').write_text(invocation)
                (self.directory / f'{prefix}-exit.json').write_text(json.dumps({
                    'invocation_id': invocation, 'native_returncode': 0, 'forced_kill': False}))
                (self.directory / f'{prefix}-identity.json').write_text(json.dumps({
                    'policy': policy, 'trace': False, 'binary_sha256': 'fixture', 'rank': node,
                    'time': step, 'pid': step + 1, 'reserve_gib': 4}))

    def test_retained_regressions_remain_unresolved(self):
        result = report(self.directory)
        self.assertEqual(len(result['points']), 80)
        self.assertFalse(result['repeat_gate_passed'])
        self.assertTrue(result['requires_investigation'])
        self.assertTrue(all(len(p['candidate_reps']) == 6 for p in result['points']))

    def test_reused_start_cannot_count_as_another_repetition(self):
        p = self.directory / '3-balanced-head-invocation.txt'
        p.write_text('cpu-fixture-head-0')
        with self.assertRaisesRegex(AssertionError, 'distinct native invocations'):
            report(self.directory)

    def test_changed_runtime_control_fails(self):
        p = self.directory / '2-latency-worker-identity.json'
        data = json.loads(p.read_text()); data['reserve_gib'] = 3.875
        p.write_text(json.dumps(data))
        with self.assertRaisesRegex(AssertionError, 'serving controls changed'):
            report(self.directory)

    def test_missing_reverse_start_fails(self):
        (self.directory / '3-balanced-mixed.jsonl').unlink()
        with self.assertRaises(FileNotFoundError):
            report(self.directory)


if __name__ == '__main__':
    unittest.main()
