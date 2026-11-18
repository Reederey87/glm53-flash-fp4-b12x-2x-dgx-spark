import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from flare_production import CapacityShortfall, validate_capacity, run_main
from flare_startup_retry import decide, record_failure, WINDOW


class StartupRetryTests(unittest.TestCase):
    def test_budget_survives_processes_and_clock_rollback(self):
        with tempfile.TemporaryDirectory() as d:
            with patch('flare_startup_retry.time.time', return_value=100):
                self.assertEqual(record_failure(d, 'a' * 32, 2287616, 2300000), 75)
            with patch('flare_startup_retry.time.time', return_value=200):
                self.assertEqual(record_failure(d, 'b' * 32, 2287616, 2300000), 75)
            with patch('flare_startup_retry.time.time', return_value=50):
                self.assertEqual(record_failure(d, 'c' * 32, 2287616, 2300000), 78)
            state = json.loads((Path(d) / 'state.json').read_text())
            self.assertEqual(state['attempts'], [100, 200])
            self.assertEqual(state['last_failure']['action'], 'budget_exhausted')
            code, state = decide(state, WINDOW + 201, 'd' * 32, 2287616, 2300000)
            self.assertEqual(code, 75)
            self.assertEqual(state['attempts'], [WINDOW + 201])

    def test_only_valid_geometry_below_floor_is_retryable(self):
        valid = 'flare_total_kv_pages 8936\nflare_kv_page_tokens 256\nflare_total_kv_tokens 2287616\n'
        with self.assertRaises(CapacityShortfall) as ctx:
            validate_capacity(valid, 2300000)
        self.assertEqual((ctx.exception.tokens, ctx.exception.minimum), (2287616, 2300000))
        for text in (valid.replace('8936', '1'), valid + valid, '', valid.replace('2287616', 'NaN')):
            try:
                validate_capacity(text, 2300000)
            except CapacityShortfall:
                self.fail('corrupt metrics must not authorize a retry')
            except ValueError:
                pass
            else:
                self.fail('corrupt metrics accepted')

    def test_corrupt_history_and_unowned_failure_fail_closed(self):
        for attempts in (None, ['100'], [True], [float('nan')], [-1]):
            with self.assertRaises(ValueError):
                decide({'schema': 1, 'attempts': attempts}, 100, 'a' * 32, 1, 2)
        with self.assertRaises(ValueError):
            decide({'schema': 1, 'attempts': []}, 100, '', 1, 2)


class UnitRestartContractTests(unittest.TestCase):
    """Only a budgeted capacity shortfall may return the retryable 75."""

    def test_success_returns_zero(self):
        with patch('flare_production.main', return_value=None):
            self.assertEqual(run_main(), 0)

    def test_budgeted_shortfall_is_the_only_retryable_outcome(self):
        shortfall = CapacityShortfall(2287616, 2300000)
        with patch('flare_production.main', side_effect=shortfall), \
                patch('flare_startup_retry.record_failure', return_value=75) as record:
            self.assertEqual(run_main(), 75)
        record.assert_called_once()

    def test_exhausted_budget_is_terminal(self):
        with patch('flare_production.main', side_effect=CapacityShortfall(1, 2300000)), \
                patch('flare_startup_retry.record_failure', return_value=78):
            self.assertEqual(run_main(), 78)

    def test_any_other_failure_is_terminal(self):
        for error in (RuntimeError('readiness deadline exceeded'), OSError('ssh down'),
                      ValueError('production pin or qualification decision does not match runtime')):
            with patch('flare_production.main', side_effect=error):
                self.assertEqual(run_main(), 78)

    def test_unattributable_shortfall_never_consumes_a_retry(self):
        with patch('flare_production.main', side_effect=CapacityShortfall(1, 2300000)), \
                patch('flare_startup_retry.record_failure',
                      side_effect=ValueError('invalid startup retry evidence')):
            self.assertEqual(run_main(), 78)


if __name__ == '__main__':
    unittest.main()


class RetryReceiptTests(unittest.TestCase):
    """Exit 75 is only honoured with a matching receipt on disk."""

    def test_retry_writes_a_receipt_and_exhausted_does_not(self):
        with tempfile.TemporaryDirectory() as d:
            with patch('flare_startup_retry.time.time', return_value=100):
                self.assertEqual(record_failure(d, 'a' * 32, 2287616, 2300000), 75)
            self.assertTrue((Path(d) / f'retry-{"a" * 32}').exists())
            with patch('flare_startup_retry.time.time', return_value=200):
                self.assertEqual(record_failure(d, 'b' * 32, 2287616, 2300000), 75)
            with patch('flare_startup_retry.time.time', return_value=300):
                self.assertEqual(record_failure(d, 'c' * 32, 2287616, 2300000), 78)
            self.assertFalse((Path(d) / f'retry-{"c" * 32}').exists())
