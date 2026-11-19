import re
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from flare_context_retrieval import build, digest


class ContextRetrievalTests(unittest.TestCase):
    def test_plants_one_code_per_depth_and_keeps_them_in_the_text(self):
        haystack, needles = build(4000, [0.05, 0.5, 0.95], 7)
        self.assertEqual(len(needles), 3)
        self.assertTrue(haystack)
        for needle in needles:
            self.assertRegex(needle['code'], r'^\d{12}$')
            self.assertIn(needle['code'], haystack)
            self.assertIn(f"section {needle['section']} is {needle['code']}", haystack)
        sections = [n['section'] for n in needles]
        self.assertEqual(sections, sorted(sections), 'deeper depths must map to later sections')
        self.assertEqual(len({n['code'] for n in needles}), 3, 'codes must be distinct')

    def test_build_is_deterministic_for_a_nonce(self):
        self.assertEqual(build(4000, [0.3], 11), build(4000, [0.3], 11))
        self.assertNotEqual(build(4000, [0.3], 11)[1][0]['code'],
                            build(4000, [0.3], 12)[1][0]['code'])

    def test_digest_is_stable(self):
        self.assertEqual(digest('abc'), digest('abc'))
        self.assertEqual(len(digest('abc')), 64)


if __name__ == '__main__':
    unittest.main()
