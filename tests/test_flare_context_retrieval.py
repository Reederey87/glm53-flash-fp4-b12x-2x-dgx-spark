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


class AnswerExtractionTests(unittest.TestCase):
    """An empty read must never masquerade as a retrieval failure."""

    def test_reads_content_reasoning_and_reasoning_content(self):
        from flare_context_retrieval import answer_text
        for message, expected in (
                ({'content': 'code 123'}, 'code 123'),
                ({'content': None, 'reasoning': 'code 456'}, 'code 456'),
                ({'content': None, 'reasoning_content': 'code 789'}, 'code 789'),
                ({'content': None, 'reasoning': None}, '')):
            data = {'choices': [{'message': message, 'finish_reason': 'stop'}]}
            text, reason = answer_text(data)
            self.assertEqual(text, expected)
            self.assertEqual(reason, 'stop')

    def test_reports_truncation(self):
        from flare_context_retrieval import answer_text
        data = {'choices': [{'message': {'content': None}, 'finish_reason': 'length'}]}
        self.assertEqual(answer_text(data), ('', 'length'))


class HardDistractorTests(unittest.TestCase):
    def test_decoys_share_the_needle_form_without_colliding(self):
        haystack, targets = build(6000, [0.2, 0.8], 3, decoys=40)
        statements = re.findall(r'section (\d+) is (\d{12})', haystack)
        target_codes = {t['code'] for t in targets}
        self.assertGreater(len(statements), 2, 'decoys must be planted')
        for target in targets:
            self.assertIn(target['code'], target_codes)
            self.assertIn(target['code'], haystack)

    def test_zero_decoys_keeps_only_targets(self):
        haystack, targets = build(6000, [0.3, 0.6], 4, decoys=0)
        self.assertEqual(len(re.findall(r'section \d+ is \d{12}', haystack)), 2)
