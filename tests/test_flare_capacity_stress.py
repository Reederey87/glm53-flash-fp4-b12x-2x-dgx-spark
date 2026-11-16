from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from flare_capacity_stress import check_requests, gauge


class CapacityStressTests(unittest.TestCase):
    def test_unobserved_concurrency_and_short_or_cached_work_fail(self):
        rows = [dict(prompt_tokens=1_000_000, completion_tokens=64, cached_tokens=0,
                     input_sha256=str(i)*64, ttft_s=100., elapsed_s=103., decode_span_s=3.) for i in range(2)]
        check_requests(rows, 2)
        with self.assertRaises(ValueError): check_requests(rows, 1)
        for key, value in (('prompt_tokens', 999999), ('completion_tokens', 63),
                           ('cached_tokens', 256), ('ttft_s', float('nan')), ('input_sha256', rows[1]['input_sha256'])):
            changed = [dict(r) for r in rows]; changed[0][key] = value
            with self.assertRaises(ValueError, msg=key): check_requests(changed, 2)

    def test_gauge_requires_one_finite_nonnegative_sample(self):
        self.assertEqual(gauge('active 2\n', 'active'), 2)
        for raw in ('active NaN\n', 'active -1\n', 'active 1\nactive 2\n', ''):
            with self.assertRaises(ValueError): gauge(raw, 'active')


if __name__ == '__main__':
    unittest.main()
