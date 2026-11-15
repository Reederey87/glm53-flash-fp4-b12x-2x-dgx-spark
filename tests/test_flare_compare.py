import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from flare_compare import compare, distributions, load


class ComparisonEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.reference = ROOT / 'receipts/flare-qualification-20261115/reference-full-bench.jsonl'
        self.records = [json.loads(line) for line in self.reference.read_text().splitlines()]
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'changed.jsonl'

    def write(self, records):
        self.path.write_text(''.join(json.dumps(row) + '\n' for row in records))

    def test_complete_reference_and_rejected_incomplete_or_duplicate_data(self):
        self.assertEqual(len(load(self.reference, 'vllm')[1]), 84)
        for rows in (self.records[:-1], self.records + [self.records[-1]]):
            self.write(rows)
            with self.assertRaises(ValueError):
                load(self.path, 'vllm')

    def test_warm_prompt_short_generation_and_invalid_timing_rejected(self):
        for field, value in (('cached_tokens', 256), ('completion_tokens', 2), ('ttft_s', float('nan'))):
            records = copy.deepcopy(self.records)
            records[1]['requests'][0][field] = value
            self.write(records)
            with self.assertRaises(ValueError):
                load(self.path, 'vllm')

    def test_request_hash_and_manifest_mismatch_cannot_compare(self):
        baseline = load(self.reference, 'vllm')
        changed = copy.deepcopy(baseline)
        changed[0]['seed'] += 1
        with self.assertRaisesRegex(ValueError, 'manifests differ'):
            compare(baseline, changed)
        changed = copy.deepcopy(baseline)
        next(iter(changed[1].values()))['requests'][0]['input_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'request bodies differ'):
            compare(baseline, changed)

    def test_noise_and_separated_regression_are_distinct(self):
        self.assertEqual(distributions([98, 100, 102], [90, 91, 92])['observation'],
                         'separated_regression_over_2pct')
        self.assertEqual(distributions([90, 100, 110], [90, 95, 101])['observation'],
                         'median_regression_repeat_needed')
        self.assertEqual(distributions([98, 100, 102], [101, 102, 103])['observation'],
                         'no_median_regression_over_2pct_observed')


if __name__ == '__main__':
    unittest.main()
