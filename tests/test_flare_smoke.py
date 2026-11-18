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




class IdleWaitTests(unittest.TestCase):
    def test_expiry_happens_at_the_supplied_limit_not_a_hardcoded_10s(self):
        # At t=11 s a hardcoded 10 s deadline would already raise; with the
        # supplied 300 s window the check must still be waiting.
        observations = [metrics(active=1)] * 3 + [metrics()]
        clock = iter([0.0] + [11.0, 20.0, 30.0, 40.0])
        with patch('flare_smoke.runtime_metrics', side_effect=observations), \
             patch('flare_smoke.time.monotonic', side_effect=lambda: next(clock)), \
             patch('flare_smoke.time.sleep'), \
             patch('flare_smoke.urllib.request.urlopen', return_value=io.BytesIO(b'')):
            with self.assertRaises(ValueError) as ctx:
                cancel_during_decode('http://test', object(), idle_wait=300)
        self.assertIn('did not reach sustained active decode', str(ctx.exception))

    def test_cli_rejects_non_finite_and_negative_waits(self):
        from flare_smoke import idle_seconds
        import argparse
        for bad in ('nan', 'inf', '-1'):
            with self.assertRaises(argparse.ArgumentTypeError):
                idle_seconds(bad)
        self.assertEqual(idle_seconds('0'), 0.0)
        self.assertEqual(idle_seconds('180'), 180.0)

    """Startup must ride out client traffic instead of failing on contact."""

    def test_busy_server_waits_for_the_configured_window(self):
        observations = [metrics(active=1), metrics(active=1), metrics()]
        with patch('flare_smoke.runtime_metrics', side_effect=observations), \
             patch('flare_smoke.time.monotonic', side_effect=[0.0, 0.0, 999.0]), \
             patch('flare_smoke.time.sleep'), \
             patch('flare_smoke.urllib.request.urlopen', return_value=io.BytesIO(b'')):
            with self.assertRaises(ValueError) as ctx:
                cancel_during_decode('http://test', object(), idle_wait=5)
        self.assertIn('still busy after 5', str(ctx.exception))

    def test_idle_window_is_used_rather_than_aborting(self):
        observations = [metrics(active=1), metrics(), metrics(generated=1)]
        with patch('flare_smoke.runtime_metrics', side_effect=observations), \
             patch('flare_smoke.time.sleep'), \
             patch('flare_smoke.urllib.request.urlopen', return_value=io.BytesIO(b'')):
            with self.assertRaises(ValueError) as ctx:
                cancel_during_decode('http://test', object(), idle_wait=30)
        # Reached the streaming phase, so the wait itself did not fail.
        self.assertIn('did not reach sustained active decode', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
