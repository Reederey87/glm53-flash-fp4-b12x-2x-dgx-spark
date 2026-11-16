import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from flare_watchdog import decision, WINDOW
from flare_production import fingerprints, validate_pin


class ProductionSafetyTests(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
