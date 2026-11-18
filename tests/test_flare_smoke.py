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




class FakeClock:
    """Deterministic clock: sleeping advances time so the wait loop terminates."""

    def __init__(self, step=5.0):
        self.now = 0.0
        self.step = step

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += max(seconds, self.step)


class IdleWaitTests(unittest.TestCase):
    """Startup must ride out client traffic instead of failing on contact."""

    def _run(self, observations, idle_wait):
        clock = FakeClock()
        opened = []

        def fake_urlopen(*args, **kwargs):
            opened.append(args[0] if args else None)
            return io.BytesIO(b'')

        with patch('flare_smoke.runtime_metrics', side_effect=observations), \
             patch('flare_smoke.time.monotonic', side_effect=clock.monotonic), \
             patch('flare_smoke.time.sleep', side_effect=clock.sleep), \
             patch('flare_smoke.urllib.request.urlopen', side_effect=fake_urlopen):
            try:
                cancel_during_decode('http://test', object(), idle_wait=idle_wait)
            except ValueError as error:
                return str(error), opened, clock.now
        return None, opened, clock.now

    def test_expiry_at_the_supplied_limit_never_opens_the_stream(self):
        message, opened, elapsed = self._run([metrics(active=1)] * 1000, idle_wait=30)
        self.assertIn('still busy after 30', message)
        self.assertEqual(opened, [])
        self.assertGreaterEqual(elapsed, 30)

    def test_a_second_limit_rules_out_a_hardcoded_120s(self):
        message, opened, elapsed = self._run([metrics(active=1)] * 1000, idle_wait=300)
        self.assertIn('still busy after 300', message)
        self.assertEqual(opened, [])
        self.assertGreaterEqual(elapsed, 300)

    def test_an_idle_window_is_used_rather_than_aborting(self):
        message, opened, _ = self._run(
            [metrics(active=1), metrics(active=1), metrics()], idle_wait=30)
        self.assertIn('did not reach sustained active decode', message)
        self.assertEqual(len(opened), 1)

    def test_cli_rejects_non_finite_and_negative_waits(self):
        import argparse
        from flare_smoke import idle_seconds
        for bad in ('nan', 'inf', '-1'):
            with self.assertRaises(argparse.ArgumentTypeError):
                idle_seconds(bad)
        self.assertEqual(idle_seconds('0'), 0.0)
        self.assertEqual(idle_seconds('180'), 180.0)


if __name__ == '__main__':
    unittest.main()
