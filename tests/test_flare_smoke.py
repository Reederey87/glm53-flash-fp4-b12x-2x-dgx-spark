import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from flare_smoke import cancel_during_decode


def metrics(generated=0, cancelled=0, active=0):
    return {'flare_generated_tokens_total': generated, 'flare_requests_cancelled_total': cancelled,
            'flare_active_requests': active, 'flare_http_inflight_requests': active,
            'flare_retiring_request_slots': 0}


def event(delta):
    return ('data: '+json.dumps({'choices':[{'delta':delta}]})+'\n').encode()


class CancellationTests(unittest.TestCase):
    def test_role_frame_is_not_decode_and_cancellation_must_drain(self):
        stream = io.BytesIO(event({'role':'assistant'}) + event({'reasoning_content':'a'*16})*20)
        observations = [metrics(), metrics(generated=32,active=1),
                        metrics(generated=33,active=1), metrics(generated=34,cancelled=1)]
        with patch('flare_smoke.urllib.request.urlopen', return_value=stream), \
             patch('flare_smoke.runtime_metrics', side_effect=observations) as read, \
             patch('flare_smoke.time.sleep'):
            result = cancel_during_decode('http://test', object())
        self.assertTrue(stream.closed)
        self.assertEqual(result['output_chunks_before_close'], 8)
        self.assertEqual(result['generated_tokens_before_close'], 32)
        self.assertEqual(result['cancelled_requests_delta'], 1)
        self.assertEqual(read.call_count, 4)
        self.assertTrue(all(v == 0 for v in result['drained_gauges'].values()))

    def test_role_only_stream_cannot_pass(self):
        stream = io.BytesIO(event({'role':'assistant'}) + b'data: [DONE]\n')
        with patch('flare_smoke.urllib.request.urlopen', return_value=stream), \
             patch('flare_smoke.runtime_metrics', return_value=metrics()):
            with self.assertRaisesRegex(ValueError,'sustained active decode'):
                cancel_during_decode('http://test', object())


if __name__ == '__main__':
    unittest.main()
