import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from flare_watchdog import decision, WINDOW
from flare_production import fingerprints, validate_pin, rollback_due, validate_capacity, capacity_floor, startup_progress, start_ranks


class ProductionSafetyTests(unittest.TestCase):
    def test_dispatches_worker_before_head_without_clearing_failure_budget(self):
        with patch('flare_production.subprocess.run') as run:
            start_ranks()
        calls = [call.args[0] for call in run.call_args_list]
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][-4:], ['systemctl', '--user', 'start', 'b12x-flare@1.service'])
        self.assertEqual(calls[1], ['systemctl', '--user', 'start', 'b12x-flare@0.service'])
        for call in run.call_args_list:
            self.assertTrue(call.kwargs['check'])
            self.assertEqual(call.kwargs['timeout'], 20)

    def test_worker_dispatch_failure_prevents_head_start(self):
        with patch('flare_production.subprocess.run', side_effect=subprocess.CalledProcessError(1, 'ssh')) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                start_ranks()
        self.assertEqual(run.call_count, 1)

    def test_worker_dispatch_wait_does_not_hide_rank_failure(self):
        started = startup_progress(['active', 'inactive'], [False, False])
        self.assertEqual(started, [True, False])
        started = startup_progress(['active', 'activating'], started)
        self.assertEqual(startup_progress(['active', 'active'], started), [True, True])
        with self.assertRaises(RuntimeError):
            startup_progress(['active', 'inactive'], started)
        for states in (['inactive', 'inactive'], ['active', 'failed'],
                       ['failed', 'active'], ['active', 'deactivating'], ['active', 'unknown']):
            with self.assertRaises(RuntimeError):
                startup_progress(states, [False, False])

    def test_provisional_release_requires_explicit_approval_and_retained_gaps(self):
        decision = {'status': 'approved-provisional', 'approved_by_user': True,
                    'minimum_kv_tokens': 2300000, 'open_gates': ['performance', 'capacity']}
        self.assertEqual(capacity_floor(decision), 2300000)
        self.assertEqual(capacity_floor({'status': 'qualified'}), 2350210)
        for change in ({'approved_by_user': False}, {'open_gates': []},
                       {'open_gates': ['']}, {'minimum_kv_tokens': 2000000},
                       {'status': 'pending'}):
            with self.assertRaises(ValueError):
                capacity_floor({**decision, **change})
        observed = 'flare_total_kv_pages 9122\nflare_kv_page_tokens 256\nflare_total_kv_tokens 2335232\n'
        self.assertEqual(validate_capacity(observed, capacity_floor(decision))['flare_total_kv_tokens'], 2335232)
        with self.assertRaises(ValueError):
            validate_capacity(observed)
        with self.assertRaises(ValueError):
            validate_capacity(observed.replace('9122', '8984').replace('2335232', '2299904'), 2300000)

    def test_production_start_requires_observed_cache_floor(self):
        def scrape(pages, tokens):
            return f'flare_total_kv_pages {pages}\nflare_kv_page_tokens 256\nflare_total_kv_tokens {tokens}\n'
        # First whole page meeting the incumbent's logical-token floor.
        good = scrape(9181, 2350336)
        self.assertEqual(validate_capacity(good)['flare_total_kv_tokens'], 2350336)
        for bad in (scrape(9180, 2350080), scrape(9122, 2335232),
                    scrape(9181, 2350335), good + 'flare_total_kv_tokens 2350336\n',
                    good.replace('2350336', 'NaN'), good.replace('256', '-256'),
                    'flare_total_kv_tokens 2350336\n'):
            with self.assertRaises(ValueError):
                validate_capacity(bad)

    def test_boot_recheck_does_not_roll_back_before_calendar_deadline(self):
        pending = {'schema': 1, 'rollback_after': 1000}
        self.assertFalse(rollback_due(pending, 999))
        self.assertTrue(rollback_due(pending, 1000))
        self.assertTrue(rollback_due(pending, 2000))
        for bad in (True, '1000', float('inf'), -1):
            with self.assertRaises(ValueError):
                rollback_due({'schema': 1, 'rollback_after': bad}, 2000)

    def test_manual_stop_disabled_maintenance_and_startup_do_not_restart(self):
        ledger = {'schema': 1, 'pending': 1, 'attempts': []}
        for state in ('inactive', 'failed', 'activating', 'deactivating'):
            action, _ = decision(ledger, 100, enabled=True, owner=state, healthy=False)
            self.assertEqual(action, 'skip')
        for enabled, maintenance in ((False, False), (True, True)):
            action, _ = decision(ledger, 100, enabled=enabled, maintenance=maintenance,
                                 owner='active', healthy=False)
            self.assertEqual(action, 'skip')

    def test_two_failed_checks_and_healthy_reset(self):
        ledger = {'schema': 1, 'pending': 0, 'attempts': []}
        args = dict(enabled=True, owner='active', healthy=False)
        action, pending = decision(ledger, 100, **args)
        self.assertEqual(action, 'observe')
        action, reset = decision(pending, 130, enabled=True, owner='active', healthy=True)
        self.assertEqual((action, reset['pending']), ('healthy', 0))
        action, consumed = decision(pending, 130, **args)
        self.assertEqual((action, consumed['attempts']), ('try_restart', [130]))

    def test_restart_budget_survives_serialization_and_clock_rollback(self):
        ledger = json.loads(json.dumps({'schema': 1, 'pending': 1,
                                      'attempts': [100, 200, 300]}))
        args = dict(enabled=True, owner='active', healthy=False)
        action, kept = decision(ledger, 50, **args)
        self.assertEqual(action, 'budget_exhausted')
        self.assertEqual(kept['attempts'], [100, 200, 300])
        action, expired = decision(ledger, WINDOW + 301, **args)
        self.assertEqual(action, 'try_restart')
        self.assertEqual(expired['attempts'], [WINDOW + 301])

    def test_corrupted_restart_ledger_fails_closed(self):
        for attempts in (None, ['yesterday'], [float('nan')], [True], [-1]):
            with self.assertRaises(ValueError):
                decision({'schema': 1, 'pending': 1, 'attempts': attempts}, 10,
                         enabled=True, owner='active', healthy=False)

    def test_recipe_core_or_decision_drift_prevents_startup(self):
        recipe = {'native_arm': 'a' * 64, 'serve_reserve_gib': 4}
        actual = fingerprints(recipe, b'accepted core')
        decision_bytes = json.dumps({'status': 'qualified', 'native_arm': 'a' * 64}).encode()
        pin = {'schema': 1, 'decision_sha256': hashlib.sha256(decision_bytes).hexdigest(),
               'ranks': {'0': actual}}
        validate_pin(pin, decision_bytes, actual, 0)
        for changed in (fingerprints({**recipe, 'serve_reserve_gib': 3}, b'accepted core'),
                        fingerprints(recipe, b'different core')):
            with self.assertRaises(ValueError):
                validate_pin(pin, decision_bytes, changed, 0)
        with self.assertRaises(ValueError):
            validate_pin(pin, decision_bytes + b' ', actual, 0)
        with self.assertRaises(ValueError):
            validate_pin(pin, decision_bytes, actual, 1)

    def test_unqualified_decision_cannot_authorize_boot(self):
        actual = fingerprints({'native_arm': 'a' * 64}, b'core')
        data = b'{"status":"pending","native_arm":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}'
        pin = {'schema': 1, 'decision_sha256': hashlib.sha256(data).hexdigest(),
               'ranks': {'0': actual}}
        with self.assertRaises(ValueError):
            validate_pin(pin, data, actual, 0)




class MemoryStateTests(unittest.TestCase):
    """The pool is sized from MemAvailable; keep the inputs beside the draw."""

    def test_records_pool_inputs(self):
        import tempfile
        from flare_production import memory_state
        with tempfile.TemporaryDirectory() as d:
            meminfo = Path(d) / 'meminfo'
            meminfo.write_text('MemTotal:       133828484 kB\n'
                               'MemFree:          2048 kB\n'
                               'MemAvailable:  117725480 kB\n'
                               'Cached:         12275560 kB\n')
            minfree = Path(d) / 'min_free_kbytes'
            minfree.write_text('1048576\n')
            state = memory_state(meminfo, minfree)
        self.assertEqual(state['MemAvailable_kb'], 117725480)
        self.assertEqual(state['Cached_kb'], 12275560)
        self.assertEqual(state['min_free_kbytes'], 1048576)

    def test_one_malformed_row_keeps_the_other_samples(self):
        import tempfile
        from flare_production import memory_state
        with tempfile.TemporaryDirectory() as d:
            meminfo = Path(d) / 'meminfo'
            meminfo.write_text('MemAvailable: 1000 kB\nCached: not-a-number kB\nMemFree: 20 kB\n')
            state = memory_state(meminfo, Path(d) / 'absent')
        self.assertEqual(state['MemAvailable_kb'], 1000)
        self.assertEqual(state['MemFree_kb'], 20)
        self.assertNotIn('Cached_kb', state)
        self.assertNotIn('min_free_kbytes', state)

    def test_presizing_samples_are_per_rank(self):
        import tempfile
        from flare_production import presizing_memory
        with tempfile.TemporaryDirectory() as d:
            for rank, value in (('head', 111), ('worker', 222)):
                (Path(d) / f'{rank}-meminfo.txt').write_text(f'MemAvailable: {value} kB\n')
            with patch.dict('os.environ', {'INVOCATION_ID': 'a' * 32}):
                state = presizing_memory(Path(d))
        self.assertEqual(state['head']['MemAvailable_kb'], 111)
        self.assertEqual(state['worker']['MemAvailable_kb'], 222)

    def test_presizing_without_a_unit_invocation_is_empty(self):
        from flare_production import presizing_memory
        with patch.dict('os.environ', {'INVOCATION_ID': ''}):
            self.assertEqual(presizing_memory(Path('/nonexistent')), {})

    def test_missing_inputs_degrade_instead_of_failing(self):
        from flare_production import memory_state
        self.assertEqual(memory_state(Path('/nonexistent/meminfo'), Path('/nonexistent/min')),
                         {})


if __name__ == '__main__':
    unittest.main()


class ProxySupervisionTests(unittest.TestCase):
    """The proxy must not stay down after a failed owner start."""

    def test_ensures_only_when_owner_is_enabled(self):
        from flare_watchdog import ensure_proxy
        with patch('flare_watchdog.subprocess.run') as run:
            self.assertEqual(ensure_proxy(False), 'disabled_owner')
        run.assert_not_called()

    def test_starts_an_inactive_proxy(self):
        from flare_watchdog import ensure_proxy
        states = [0, 'inactive']
        with patch('flare_watchdog.subprocess.run') as run, \
             patch('flare_watchdog.state', side_effect=lambda unit: states.pop(0)), \
             patch('flare_watchdog.command') as dispatch:
            run.return_value.returncode = 0
            self.assertEqual(ensure_proxy(True), 'started')
        dispatch.assert_called_once()
        argv = dispatch.call_args[0][0]
        self.assertIn('start', argv)
        self.assertIn('--no-block', argv)
        self.assertEqual(argv[-1], 'b12x-flare-tailscale.service')

    def test_leaves_an_active_proxy_alone(self):
        from flare_watchdog import ensure_proxy
        with patch('flare_watchdog.subprocess.run') as run, \
             patch('flare_watchdog.state', return_value='active'), \
             patch('flare_watchdog.command') as dispatch:
            run.return_value.returncode = 0
            self.assertEqual(ensure_proxy(True), 'active')
        dispatch.assert_not_called()

    def test_disabled_proxy_is_not_started(self):
        from flare_watchdog import ensure_proxy
        with patch('flare_watchdog.subprocess.run') as run, \
             patch('flare_watchdog.state', return_value='inactive'), \
             patch('flare_watchdog.command') as dispatch:
            run.return_value.returncode = 1
            self.assertEqual(ensure_proxy(True), 'not_enabled')
        dispatch.assert_not_called()
