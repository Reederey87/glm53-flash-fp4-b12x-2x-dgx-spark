import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from flare_bench import prompt_ids, validate_prefill

class ExactBenchmarkTests(unittest.TestCase):
    def test_matched_exact_fixtures_and_distinct_prefixes(self):
        a=prompt_ids(list(range(1000,2000)),8192,[1,0,4,8192,0])
        self.assertEqual(len(a),8192)
        self.assertEqual(a,prompt_ids(list(range(1000,2000)),8192,[1,0,4,8192,0]))
        b=prompt_ids(list(range(1000,2000)),8192,[1,0,4,8192,1])
        self.assertNotEqual(a[:256],b[:256])

    def test_prefill_rejects_mismatched_tokens_or_cache_hits(self):
        validate_prefill([{'prompt_tokens':8192,'cached_tokens':0}],8192)
        for row in [{'prompt_tokens':8191,'cached_tokens':0},{'prompt_tokens':8192,'cached_tokens':256}]:
            with self.assertRaises(ValueError):validate_prefill([row],8192)
