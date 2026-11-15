import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from flare_retrieval import graph_delta, requests, summarize


class Fixture:
    def fixture(self, size, nonce, seed, max_tokens, model):
        return {'messages': [{'content': nonce + ' private fixture'}], 'seed': seed}, 'private answer', 3

    def classify(self, response, code, record):
        return 'correct', response['choices'][0]['message']['content']


class RetrievalTests(unittest.TestCase):
    def test_cold_prefixes_and_fork_suffixes(self):
        fixture = Fixture()
        cold = requests(fixture, 'cold', 8000, 'run', 1101, 4, 'model')
        self.assertEqual(len({r[0]['messages'][0]['content'].split()[0] for r in cold}), 4)
        forks = requests(fixture, 'fork', 8000, 'run', 1101, 4, 'model')
        self.assertEqual(len({r[0]['messages'][0]['content'].split('\n')[0] for r in forks}), 1)
        self.assertEqual(len({r[0]['messages'][0]['content'] for r in forks}), 4)

    def test_observed_cache_and_sanitized_receipt(self):
        fixture = Fixture()
        item = requests(fixture, 'cold', 8000, 'run', 1101, 1, 'model')[0]
        response = {'choices': [{'message': {'content': 'private answer'}}],
                    'usage': {'prompt_tokens': 8000, 'completion_tokens': 100,
                              'prompt_tokens_details': {'cached_tokens': 0}}}
        result = summarize(fixture, item, response, 1.0, 'cold')
        self.assertTrue(result['cache_observation_passed'])
        self.assertNotIn('private', json.dumps(result))
        self.assertFalse(summarize(fixture, item, response, 1.0, 'fork')['cache_observation_passed'])
        response['usage']['prompt_tokens_details']['cached_tokens'] = 4096
        self.assertTrue(summarize(fixture, item, response, 1.0, 'fork')['cache_observation_passed'])
        self.assertFalse(summarize(fixture, item, response, 1.0, 'cold')['cache_observation_passed'])
        self.assertEqual(summarize(fixture, item, {'error': 'private error'}, 1.0, 'cold')['verdict'], 'error')

    def test_graph_counter_reset_and_no_observation_fail(self):
        self.assertEqual(graph_delta({(4, 4): 10}, {(4, 4): 15, (1, 4): 2}), {'4x4': 5, '1x4': 2})
        for before, after in ((None, {}), ({}, {}), ({(4, 4): 10}, {(4, 4): 1}), ({(4, 4): 1}, {})):
            with self.assertRaises(ValueError):
                graph_delta(before, after)
