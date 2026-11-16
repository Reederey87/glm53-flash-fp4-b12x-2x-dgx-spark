import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from flare_lifecycle import check_result, native_exit, state
import json


class LifecycleEvidenceTests(unittest.TestCase):
    native = {'native_returncode': 0, 'forced_kill': False, 'shutdown_requested': True}
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
        check_result('graceful', [clean, clean], [self.native, self.native])
        check_result('graceful', [clean, clean],
                     [self.native, dict(self.native, shutdown_requested=False)])
        with self.assertRaisesRegex(ValueError, 'not clean'):
            check_result('graceful', [failed, clean], [self.native, self.native])
        with self.assertRaisesRegex(ValueError, 'not reported'):
            check_result('peer-failure', [clean, failed], [self.native])
        check_result('peer-failure', [failed, failed], [self.native])

    def test_collected_service_success_cannot_hide_child_failure(self):
        clean = {'ActiveState': 'inactive', 'MainPID': '0', 'Result': 'success', 'ExecMainStatus': '0'}
        for evidence in ([], [self.native], [self.native, dict(self.native, native_returncode=-9)],
                         [self.native, dict(self.native, forced_kill=True)],
                         [dict(self.native, shutdown_requested=False), self.native]):
            with self.assertRaisesRegex(ValueError, 'native children'):
                check_result('graceful', [clean, clean], evidence)

    def test_native_evidence_must_belong_to_this_invocation(self):
        result = dict(self.native, schema=1, event='native_exit', action='serve',
                      rank=0, invocation_id='a'*32, native_pid=123)
        with patch('flare_lifecycle.command', return_value=json.dumps(result)):
            self.assertEqual(native_exit(0, 'a'*32), result)
            with self.assertRaisesRegex(ValueError, 'mismatched native'):
                native_exit(0, 'b'*32)
            with self.assertRaisesRegex(ValueError, 'mismatched native'):
                native_exit(1, 'a'*32)

    def test_remaining_rank_blocks_both_verdicts(self):
        stopped = {'ActiveState': 'inactive', 'MainPID': '0', 'Result': 'success', 'ExecMainStatus': '0'}
        for remaining in (dict(stopped, ActiveState='active'), dict(stopped, MainPID='123')):
            for action in ('graceful', 'peer-failure'):
                with self.assertRaisesRegex(ValueError, 'did not terminate'):
                    check_result(action, [stopped, remaining], [])


if __name__ == '__main__':
    unittest.main()
