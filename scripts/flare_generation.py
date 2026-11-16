"""Frozen public generation corpus: 64-token probes and separate answer checks.

No server lifecycle actions. Retain complete public responses for diagnosis.
The longer answer phase is not represented as a completed 64-token response.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time
import urllib.request

MODEL = 'nvidia/GLM-5.3-Flash-FP4-Local'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False).encode()).hexdigest()


def schema(value):
    if type(value) is dict:
        return {'type': 'object', 'properties': {k: schema(v) for k, v in value.items()},
                'required': list(value), 'additionalProperties': False}
    if type(value) is list:
        assert value and all(type(v) is type(value[0]) for v in value)
        return {'type': 'array', 'items': schema(value[0])}
    return {'type': {str: 'string', int: 'integer', bool: 'boolean'}[type(value)]}


def fixtures():
    rows = []
    simple = [
        ('Reply with only the word hello.', 'hello'),
        ('What is 2+2? Reply only with the number.', '4'),
        ('What is 7-3? Reply only with the number.', '4'),
        ('What is 3 times 5? Reply only with the number.', '15'),
        ('What is 12 divided by 4? Reply only with the number.', '3'),
        ('Reply with the uppercase form of fjord and nothing else.', 'FJORD'),
        ('Reply with the lowercase form of HARBOR and nothing else.', 'harbor'),
        ('Reverse the letters in abc. Reply only with the result.', 'cba'),
        ('Which is larger, 9 or 4? Reply only with the number.', '9'),
        ('How many items are in [red, blue, green]? Reply only with the number.', '3'),
        ('The note says the vessel is named Aurora. Reply only with the vessel name.', 'Aurora'),
        ('The departure time is 09:15. Reply only with that time.', '09:15'),
        ('The manifest lists 24 crates. Reply only with the crate count.', '24'),
        ('Translate the English word cat into French. Reply with one word.', 'chat'),
        ('What is the capital of France? Reply with the city only.', 'Paris'),
        ('What is the chemical symbol for oxygen? Reply with the symbol only.', 'O'),
        ('Reply only with the next letter in A, B, C.', 'D'),
        ('The code is LANTERN73. Copy the code exactly, without explanation.', 'LANTERN73'),
        ('Which word comes first alphabetically: zebra or apple? Reply with that word only.', 'apple'),
        ('A box contains two red balls and one blue ball. How many balls total? Reply only with the number.', '3'),
    ]
    for i, (prompt, expected) in enumerate(simple):
        rows.append({'id': f'chat-{i:02}', 'category': 'chat', 'prompt': prompt,
                     'expected': expected, 'options': {}})
    for i, city in enumerate(('Oslo', 'Tokyo', 'Paris', 'Lima', 'Dublin', 'Rome', 'Cairo', 'Seoul', 'Lisbon', 'Helsinki')):
        tool = {'type': 'function', 'function': {'name': 'get_temperature',
                'description': 'Read the temperature in a city.',
                'parameters': schema({'city': city})}}
        rows.append({'id': f'tool-{i:02}', 'category': 'tool',
                     'prompt': f'Call get_temperature for {city}. Use exactly that city spelling.',
                     'expected': {'city': city}, 'options': {'tools': [tool],
                     'tool_choice': {'type': 'function', 'function': {'name': 'get_temperature'}}}})
    objects = [{'ok': True}, {'count': 3}, {'city': 'Oslo'}, {'code': 'SPARK42'},
               {'ready': False}, {'values': [2, 4, 6]}, {'port': 'Bergen', 'berth': 7},
               {'tags': ['red', 'blue']}, {'total': 15, 'unit': 'kg'}, {'name': 'Aurora', 'active': True}]
    for i, expected in enumerate(objects):
        rows.append({'id': f'json-{i:02}', 'category': 'json',
                     'prompt': 'Return exactly this JSON object: ' + json.dumps(expected),
                     'expected': expected, 'options': {'response_format': {'type': 'json_schema',
                     'json_schema': {'name': 'fixture', 'strict': True, 'schema': schema(expected)}}}})
    for i in range(10):
        repetitions = (1024, 2048, 4096, 8192, 16384)[i // 2]
        code = f'HARBOR{i:02}K{73 + i}'
        filler = 'Cargo manifest placeholder. No access code is recorded on this line.\n'
        split = repetitions // (4 if i % 2 == 0 else 1)
        passage = filler * split + f'Authoritative record: access code = {code}.\n' + filler * (repetitions - split)
        rows.append({'id': f'long-{i:02}', 'category': 'long',
                     'prompt': passage + '\nCopy only the access code from the authoritative record.',
                     'expected': code, 'filler_repetitions': repetitions, 'options': {}})
    assert len(rows) == 50 and len({r['id'] for r in rows}) == 50
    return rows


def body(case, run_id, budget):
    return {'model': MODEL, 'messages': [{'role': 'user',
            'content': f'Public qualification {run_id}/{case["id"]}.\n' + case['prompt']}],
            'temperature': 1., 'top_p': .95, 'seed': 531716, 'reasoning_effort': 'low',
            'max_tokens': budget, **case['options']}


def equal(actual, expected):
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(equal(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(equal(a, b) for a, b in zip(actual, expected))
    return actual == expected


def verdict(case, response, budget):
    try:
        choices = response['choices']
        assert type(choices) is list and len(choices) == 1 and type(choices[0]['index']) is int and choices[0]['index'] == 0
        choice = choices[0]; message = choice['message']; usage = response['usage']
        assert type(message) is dict and message['role'] == 'assistant'
        assert all(message.get(k) is None or type(message[k]) is str for k in ('content', 'reasoning_content', 'reasoning'))
        n = usage['completion_tokens']; prompt = usage['prompt_tokens']
        assert type(n) is int and 0 < n <= budget and type(prompt) is int and prompt > 0
        assert choice['finish_reason'] in ('stop', 'tool_calls', 'length')
        assert message.get('content') or message.get('reasoning_content') or message.get('reasoning') or message.get('tool_calls')
        assert response['model'] == MODEL and 'error' not in response
        structural = True
    except (AssertionError, KeyError, IndexError, TypeError, AttributeError):
        return {'structural_passed': False, 'answer_passed': False, 'reason': 'response contract'}
    answer = False
    try:
        if case['category'] == 'tool':
            calls = message.get('tool_calls', [])
            answer = (len(calls) == 1 and calls[0]['function']['name'] == 'get_temperature'
                      and equal(json.loads(calls[0]['function']['arguments']), case['expected']))
        elif case['category'] == 'json':
            answer = equal(json.loads(message.get('content') or ''), case['expected']) and not message.get('tool_calls')
        else:
            actual = (message.get('content') or '').strip().strip('`"\' .!\n').casefold()
            answer = actual == case['expected'].casefold() and not message.get('tool_calls')
    except (KeyError, IndexError, TypeError, ValueError):
        pass
    return {'structural_passed': structural, 'answer_passed': answer and choice['finish_reason'] != 'length',
            'budget_exhausted': choice['finish_reason'] == 'length', 'prompt_tokens': prompt,
            'completion_tokens': n, 'cached_tokens': (usage.get('prompt_tokens_details') or {}).get('cached_tokens')}


def load(path):
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    manifest = rows[0]['manifest']; cases = fixtures()
    assert manifest['schema'] == 1 and manifest['fixture_sha256'] == digest(cases)
    assert manifest['engine'] in ('vllm', 'flare') and manifest['budgets'] == [64, 1024]
    assert len(rows) == 102 and rows[-1] == {'complete': True, 'cases': 50, 'requests': 100}
    for row, (case, budget) in zip(rows[1:-1], ((c, b) for c in cases for b in (64, 1024)), strict=True):
        assert row['id'] == case['id'] and row['budget'] == budget
        assert row['request_sha256'] == digest(body(case, manifest['run_id'], budget))
        assert row['response_sha256'] == digest(row['response'])
        assert row['verdict'] == verdict(case, row['response'], budget)
    return manifest, rows[1:-1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    run = sub.add_parser('run'); run.add_argument('--base', required=True)
    run.add_argument('--engine', choices=('vllm', 'flare'), required=True)
    run.add_argument('--run-id', required=True); run.add_argument('--out', type=Path, required=True)
    check = sub.add_parser('compare'); check.add_argument('--reference', type=Path, required=True)
    check.add_argument('--candidate', type=Path, required=True); check.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.action == 'compare':
        bm, br = load(a.reference); cm, cr = load(a.candidate)
        assert bm['engine'] == 'vllm' and cm['engine'] == 'flare'
        assert {k: v for k, v in bm.items() if k != 'engine'} == {k: v for k, v in cm.items() if k != 'engine'}
        details = {}
        for name, rows in (('reference', br), ('candidate', cr)):
            details[name] = {'structural_failures': [r['id'] + '/' + str(r['budget']) for r in rows if not r['verdict']['structural_passed']],
                'answer_failures': [r['id'] for r in rows if r['budget'] == 1024 and not r['verdict']['answer_passed']],
                'probe_budget_exhaustions': [r['id'] for r in rows if r['budget'] == 64 and r['verdict'].get('budget_exhausted')]}
        result = {'schema': 1, 'details': details, 'passed': all(not d['structural_failures'] and not d['answer_failures'] for d in details.values()),
                  'scope': '50 public 64-token generation probes and separate 1024-budget semantic answers per engine; not numerical logit equivalence'}
        with a.out.open('x') as f:
            json.dump(result, f, indent=2); f.write('\n')
        print(json.dumps(result), flush=True)
        return
    cases = fixtures()
    with a.out.open('x') as output:
        def emit(row):
            output.write(json.dumps(row, ensure_ascii=False) + '\n'); output.flush()
        emit({'manifest': {'schema': 1, 'engine': a.engine, 'run_id': a.run_id,
                          'fixture_sha256': digest(cases), 'budgets': [64, 1024]}})
        for case in cases:
            for budget in (64, 1024):
                request = body(case, a.run_id, budget)
                start = time.monotonic()
                req = urllib.request.Request(a.base.rstrip('/') + '/v1/chat/completions', json.dumps(request).encode(),
                                             {'Content-Type': 'application/json'})
                with urllib.request.urlopen(req, timeout=1800) as reply:
                    response = json.load(reply)
                row = {'id': case['id'], 'budget': budget, 'request_sha256': digest(request),
                       'response': response, 'response_sha256': digest(response),
                       'elapsed_s': time.monotonic() - start, 'verdict': verdict(case, response, budget)}
                emit(row)
                print(json.dumps({k: v for k, v in row.items() if k != 'response'}), flush=True)
        emit({'complete': True, 'cases': 50, 'requests': 100})


if __name__ == '__main__':
    main()
