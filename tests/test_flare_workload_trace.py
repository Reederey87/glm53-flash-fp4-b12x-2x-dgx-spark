import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'qualification'))
from analyze_workload_trace import analyze


class WorkloadTraceTests(unittest.TestCase):
    def fixture(self, policy):
        root = ROOT / 'receipts/flare-qualification-20261115'
        rows = [json.loads(x) for x in (root / f'bounded-native-{policy}-trace.jsonl').read_text().splitlines()]
        client = [json.loads(x) for x in (root / f'bounded-native-{policy}-mixed.jsonl').read_text().splitlines()]
        return rows, [128] + [r['prompt_tokens'] for r in client if r.get('event') == 'request']

    def test_retained_complete_traces(self):
        for policy, count in (('balanced', 414), ('latency', 405)):
            report = analyze(*self.fixture(policy))
            self.assertEqual(report['native_histories'], 26)
            self.assertEqual(report['completions'], count)

    def test_missing_history_and_fence(self):
        rows, lengths = self.fixture('balanced')
        with self.assertRaises(AssertionError):
            analyze(rows, lengths + [128])
        index = next(i for i, r in enumerate(rows) if r['event'] == 'completion')
        with self.assertRaises(AssertionError):
            analyze(rows[:index] + rows[index + 1:], lengths)

    def test_loss_or_expired_capture_is_rejected(self):
        rows, lengths = self.fixture('balanced')
        for update in ({'dropped_updates': 1}, {'reason': 'duration'}, {'truncated': True}):
            with self.assertRaises(AssertionError):
                analyze(rows[:-1] + [dict(rows[-1], **update)], lengths)
