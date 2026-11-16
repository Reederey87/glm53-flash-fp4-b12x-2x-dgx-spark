import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from flare_lifecycle import check_result, state


class LifecycleEvidenceTests(unittest.TestCase):
    # Actual six-field shape returned by systemd on the head during the trial.
    observed = ('MainPID=760169\nResult=success\nExecMainCode=0\nExecMainStatus=0\n'
                'ActiveState=active\nSubState=running\n')

    def test_observed_systemd_state_is_accepted(self):
        with patch('flare_lifecycle.command', return_value=self.observed):
            result = state(0)
        self.assertEqual(result['ActiveState'], 'active')
        self.assertEqual(result['MainPID'], '760169')

    def test_incomplete_or_substituted_state_is_rejected(self):
        for text in (self.observed.replace('Result=success\n', ''),
                     self.observed.replace('Result=success', 'Unrelated=success'),
                     self.observed.replace('Result=success', 'Result=')):
            with self.subTest(text=text), patch('flare_lifecycle.command', return_value=text):
                with self.assertRaisesRegex(ValueError, 'missing unit state'):
                    state(0)

    def test_failure_cannot_be_mistaken_for_clean_stop(self):
        clean = {'ActiveState': 'inactive', 'MainPID': '0', 'Result': 'success', 'ExecMainStatus': '0'}
        failed = dict(clean, ActiveState='failed', Result='exit-code', ExecMainStatus='1')
        check_result('graceful', [clean, clean])
        with self.assertRaisesRegex(ValueError, 'not clean'):
            check_result('graceful', [failed, clean])
        with self.assertRaisesRegex(ValueError, 'not reported'):
            check_result('peer-failure', [clean, failed])
        check_result('peer-failure', [failed, failed])

    def test_remaining_rank_blocks_both_verdicts(self):
        stopped = {'ActiveState': 'inactive', 'MainPID': '0', 'Result': 'success', 'ExecMainStatus': '0'}
        for remaining in (dict(stopped, ActiveState='active'), dict(stopped, MainPID='123')):
            for action in ('graceful', 'peer-failure'):
                with self.assertRaisesRegex(ValueError, 'did not terminate'):
                    check_result(action, [stopped, remaining])


if __name__ == '__main__':
    unittest.main()
