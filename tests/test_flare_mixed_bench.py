import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from flare_mixed_bench import summarize, validate_overlap


class MixedObservationTests(unittest.TestCase):
    def setUp(self):
        self.body = {'prompt': [11, 22, 33], 'max_tokens': 4}
        self.usage = {'prompt_tokens': 3, 'completion_tokens': 4,
                      'prompt_tokens_details': {'cached_tokens': 0}}

    def test_delivery_burst_does_not_invent_token_timestamps(self):
        row = summarize(self.body, 0, .3, [.1, .2], self.usage, True, '0'*64)
        self.assertEqual(row['completion_tokens'], 4)
        self.assertEqual(len(row['delivery_times_s']), 2)
        self.assertAlmostEqual(row['delivery_gap_p95_s'], .1)

    def test_missing_usage_truncation_or_cache_hit_is_not_success(self):
        for field, value in [('completion_tokens', 3), ('completion_tokens', True),
                             ('prompt_tokens', 2), ('prompt_tokens_details', {}),
                             ('prompt_tokens_details', {'cached_tokens': 1})]:
            usage = copy.deepcopy(self.usage)
            usage[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                summarize(self.body, 0, .3, [.1,.2], usage, True, '0'*64)
        for usage, done, deliveries in [(None,True,[.1]), (self.usage,False,[.1]),
                                       (self.usage,True,[])]:
            with self.assertRaises(ValueError):
                summarize(self.body, 0, .3, deliveries, usage, done, '0'*64)

    def test_nonmonotonic_or_nonfinite_timing_is_rejected(self):
        for times in ([.2,.1], [.1,float('nan')], [.1,.4]):
            with self.assertRaises(ValueError):
                summarize(self.body, 0, .3, times, self.usage, True, '0'*64)

    def test_overlap_requires_both_decoders_to_progress_after_prompt_arrival(self):
        rows = [{'id': 'long', 'start_s': 1, 'end_s': 10},
                {'id': 'short', 'start_s': 1.1, 'end_s': 4}]
        rows += [{'id': f'decode{i}', 'end_s': 8,
                  'delivery_times_s': [.5,2,3,4,5,6,7]} for i in range(2)]
        result = validate_overlap(rows)
        self.assertEqual(result['decode_deliveries_during_interval'], {'decode0':6,'decode1':6})
        for changes in ({'end_s': .9}, {'delivery_times_s': [2,3,4,5,6,7]},
                        {'delivery_times_s': [.5,2,3]}):
            invalid = copy.deepcopy(rows)
            invalid[-1].update(changes)
            with self.assertRaises(ValueError):
                validate_overlap(invalid)
