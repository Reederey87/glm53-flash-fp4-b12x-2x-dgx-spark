import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from flare_lifecycle import check_result


class LifecycleEvidenceTests(unittest.TestCase):
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
