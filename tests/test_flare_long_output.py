import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from flare_long_output import LENGTHS, bodies, compare, load
from flare_mixed_bench import summarize
from spec_metrics import COUNTERS, counter_delta


def fixture(policy):
    records = [{'manifest': {'schema': 2, 'ignore_eos': True, 'policy': policy, 'reps': 3,
        'lengths': list(LENGTHS), 'output_budget': 256, 'temperature': 1,
        'top_p': .95, 'slot_cap': 4, 'run_id': 'test', 'tokenizer_sha256': 'a'*64}}]
    for rep in range(3):
        rows = []
        for i, length in enumerate(LENGTHS):
            body = {'max_tokens': 256, 'identity': [rep, i]}
            rows.append(summarize(body, .01, 11, [1, 2, 4, 8, 10],
                {'prompt_tokens': length, 'completion_tokens': 256,
                 'prompt_tokens_details': {'cached_tokens': 0}}, True, 'b'*64))
        before = {name: 0 for name in COUNTERS['flare'].values()}
        after = {COUNTERS['flare'][name]: n for name, n in
                 {'accepted': 80, 'draft_tokens': 150, 'drafts': 50, 'rounds': 60}.items()}
        records.append({'rep': rep, 'requests': rows, 'wall_s': 12,
            'counters_before': before, 'counters_after': after,
            'speculative_delta': counter_delta(before, after, 'flare')})
    return records + [{'complete': True, 'requests': 12}]


class LongOutputTests(unittest.TestCase):
    def test_fixtures_match_across_arms_with_distinct_cold_prefixes(self):
        a = bodies(list(range(1000, 2000)), 'trial', 0)
        self.assertEqual(a, bodies(list(range(1000, 2000)), 'trial', 0))
        self.assertEqual([len(r['prompt']) for r in a], list(LENGTHS))
        self.assertEqual({r['max_tokens'] for r in a}, {256})
        self.assertTrue(all(r['ignore_eos'] is True for r in a))
        self.assertEqual(len({tuple(r['prompt'][:256]) for r in a}), 4)

    def test_complete_comparison_and_corrupt_evidence_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            b, c = (Path(directory)/name for name in ('b', 'c'))
            def write(path, records):
                path.write_text(''.join(json.dumps(r)+'\n' for r in records))
            write(b, fixture('balanced')); write(c, fixture('latency'))
            self.assertEqual(len(compare(b, c)['points']), 17)
            for change in ('partial', 'cached', 'short', 'hash', 'counter', 'timing', 'eos-policy'):
                rows = fixture('latency')
                row = rows[1]['requests'][0]
                if change == 'eos-policy': rows[0]['manifest']['ignore_eos'] = False
                if change == 'partial': rows.pop()
                if change == 'cached': row['cached_tokens'] = 256
                if change == 'short': row['completion_tokens'] = 1
                if change == 'hash': row['input_sha256'] = hashlib.sha256(b'different').hexdigest()
                if change == 'counter': rows[1]['speculative_delta']['accepted'] += 1
                if change == 'timing': rows[1]['wall_s'] = float('nan')
                write(c, rows)
                with self.assertRaises(ValueError, msg=change):
                    compare(b, c)
