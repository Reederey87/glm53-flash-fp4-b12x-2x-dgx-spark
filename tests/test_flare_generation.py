import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from flare_generation import MODEL, body, digest, equal, fixtures, load, verdict


def response(content='hello', finish='stop'):
    return {'model': MODEL, 'choices': [{'index': 0, 'finish_reason': finish,
            'message': {'role': 'assistant', 'content': content}}],
            'usage': {'prompt_tokens': 30, 'completion_tokens': 10}}


class GenerationTests(unittest.TestCase):
    def test_truncation_is_not_semantic_success(self):
        case = fixtures()[0]
        self.assertTrue(verdict(case, response(), 64)['answer_passed'])
        result = verdict(case, response(finish='length'), 64)
        self.assertTrue(result['structural_passed'])
        self.assertFalse(result['answer_passed'])
        self.assertTrue(result['budget_exhausted'])

    def test_tool_arguments_and_json_types_are_checked(self):
        case = fixtures()[20]
        result = response(None, 'tool_calls')
        result['choices'][0]['message']['tool_calls'] = [{'function': {
            'name': 'get_temperature', 'arguments': '{"city":"Oslo"}'}}]
        self.assertTrue(verdict(case, result, 1024)['answer_passed'])
        result['choices'][0]['message']['tool_calls'][0]['function']['arguments'] = '{"city":"Tokyo"}'
        self.assertFalse(verdict(case, result, 1024)['answer_passed'])
        self.assertFalse(equal({'ok': 1}, {'ok': True}))
        self.assertFalse(verdict(fixtures()[30], response('{"ok":1}'), 1024)['answer_passed'])

    def test_bad_usage_and_message_fail_closed(self):
        for kind in ('usage', 'role', 'message', 'model'):
            value = response()
            if kind == 'usage': value['usage']['completion_tokens'] = 65
            if kind == 'role': value['choices'][0]['message']['role'] = 'user'
            if kind == 'message': value['choices'][0]['message'] = 'invalid'
            if kind == 'model': value['model'] = 'other'
            self.assertFalse(verdict(fixtures()[0], value, 64)['structural_passed'], kind)

    def test_complete_receipt_rejects_changed_or_missing_requests(self):
        cases = fixtures()
        self.assertEqual(len(cases), 50)
        self.assertEqual({c['category'] for c in cases}, {'chat', 'tool', 'json', 'long'})
        rows = [{'manifest': {'schema': 1, 'fixture_sha256': digest(cases),
                             'engine': 'flare', 'run_id': 'unit', 'budgets': [64, 1024]}}]
        for case in cases:
            for budget in (64, 1024):
                value = response()
                rows.append({'id': case['id'], 'budget': budget,
                    'request_sha256': digest(body(case, 'unit', budget)),
                    'response': value, 'response_sha256': digest(value),
                    'verdict': verdict(case, value, budget)})
        rows.append({'complete': True, 'cases': 50, 'requests': 100})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'receipt.jsonl'
            def write(data):
                path.write_text(''.join(json.dumps(r) + '\n' for r in data))
            write(rows); self.assertEqual(len(load(path)[1]), 100)
            write(rows[:-1])
            with self.assertRaises(AssertionError): load(path)
            rows[1]['request_sha256'] = '0' * 64
            write(rows)
            with self.assertRaises(AssertionError): load(path)


if __name__ == '__main__':
    unittest.main()
