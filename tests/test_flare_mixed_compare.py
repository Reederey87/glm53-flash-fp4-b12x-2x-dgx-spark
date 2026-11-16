import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from flare_mixed_bench import summarize, validate_overlap
from flare_mixed_compare import CASES, compare, distribution, load


def fixture(policy):
    records = [{'manifest': {'schema': 1, 'policy': policy, 'reps': 3, 'slot_cap': 4,
                'temperature': 1, 'top_p': .95, 'run_id': 'fixture', 'tokenizer_sha256': 'f'*64}}]
    for rep in range(3):
        for case, items in CASES.items():
            rows = []
            for name, (length, budget, offset) in items.items():
                body = {'max_tokens': budget, 'identity': [rep, case, name]}
                start = offset if offset is not None else 2
                deliveries = [start+1] if budget == 1 else [1, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 7]
                if name == 'long':
                    deliveries = [6 if case == 'decode_overlap' else 40]
                end = deliveries[-1] + .01
                row = {'event': 'request', 'rep': rep, 'case': case, 'id': name,
                       'scheduled_offset_s': offset,
                       **summarize(body, start, end, deliveries,
                                   {'completion_tokens': budget, 'prompt_tokens': length or 128,
                                    'prompt_tokens_details': {'cached_tokens': 0}}, True,
                                   hashlib.sha256(name.encode()).hexdigest())}
                rows.append(row)
            records.extend(rows)
            records.append({'event': 'case_complete', 'rep': rep, 'case': case,
                            'wall_s': max(r['end_s'] for r in rows)+.01,
                            'request_count': len(rows),
                            'overlap': validate_overlap(rows) if case == 'decode_overlap' else None})
    return records + [{'complete': True, 'cases': 9, 'requests': 75}]


class MixedComparisonTests(unittest.TestCase):
    def test_diagnostic_repetition_cannot_pass_qualification(self):
        rows = fixture('latency')
        rows[0]['manifest']['reps'] = 1
        rows = [r for r in rows if r.get('rep', 0) == 0]
        rows[-1] = {'complete': True, 'cases': 3, 'requests': 25}
        with self.assertRaises(ValueError):
            self.read(rows, 'latency')

    def read(self, records, policy='balanced'):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'fixture.jsonl'
            path.write_text(''.join(json.dumps(r)+'\n' for r in records))
            return load(path, policy)

    def test_complete_matched_workloads_and_metric_direction(self):
        result = compare(self.read(fixture('balanced')), self.read(fixture('latency'), 'latency'))
        self.assertTrue(all(p['median_change_pct'] == 0 for p in result))
        self.assertTrue(all(len(p['reference_reps']) == 3 for p in result))
        self.assertEqual(distribution([1, 1, 1], [1.03]*3)['observation'], 'separated_regression_over_2pct')
        self.assertEqual(distribution([1]*3, [.97]*3, True)['observation'], 'separated_regression_over_2pct')
        self.assertEqual(distribution([1, 2, 3], [2, 3, 4])['observation'], 'median_regression_repeat_needed')

    def test_partial_duplicate_and_failed_receipts_rejected(self):
        original = fixture('balanced')
        for records in (original[:-1], original[:1]+original[2:],
                        original[:2]+original[1:],
                        original[:1]+[{'event': 'request_error', 'rep': 0, 'case': 'unequal_burst'}]+original[1:]):
            with self.assertRaises(ValueError):
                self.read(records)

    def test_cold_timing_and_overlap_evidence_checked(self):
        for field, value in (('cached_tokens', 1), ('ttft_s', 9), ('start_s', .3),
                             ('completion_tokens', 0), ('delivery_gap_max_s', 0)):
            records = fixture('balanced')
            records[1][field] = value
            with self.assertRaises(ValueError):
                self.read(records)
        records = fixture('balanced')
        next(r for r in records if r.get('event') == 'case_complete' and r['case'] == 'decode_overlap')['overlap'] = {}
        with self.assertRaises(ValueError):
            self.read(records)

    def test_mismatched_bodies_and_manifest_rejected(self):
        baseline = self.read(fixture('balanced'))
        candidate = fixture('latency')
        candidate[1]['input_sha256'] = 'a'*64
        with self.assertRaisesRegex(ValueError, 'bodies differ'):
            compare(baseline, self.read(candidate, 'latency'))
        candidate = fixture('latency')
        candidate[0]['manifest']['run_id'] = 'different'
        with self.assertRaisesRegex(ValueError, 'manifests differ'):
            compare(baseline, self.read(candidate, 'latency'))


if __name__ == '__main__':
    unittest.main()
