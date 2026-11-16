from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from flare_memory_watch import GIB, memory, notify_healthy, queue_restore, violations


class MemoryWatchTests(unittest.TestCase):
    def test_readiness_and_heartbeat_require_healthy_observation(self):
        with tempfile.TemporaryDirectory() as directory:
            address = str(Path(directory)/'notify')
            with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as receiver:
                receiver.bind(address)
                receiver.settimeout(.05)
                with patch.dict('os.environ', {'NOTIFY_SOCKET': address}):
                    for sample in ({'violations': ['head:MemFree']}, {'observation_error': 'TimeoutExpired'}):
                        self.assertFalse(notify_healthy(sample, False))
                        with self.assertRaises(TimeoutError):
                            receiver.recv(128)
                    self.assertTrue(notify_healthy({'violations': []}, False))
                    self.assertEqual(receiver.recv(128), b'READY=1\nWATCHDOG=1')
                    self.assertTrue(notify_healthy({'violations': []}, True))
                    self.assertEqual(receiver.recv(128), b'WATCHDOG=1')

    def test_notification_failure_is_visible_to_systemd(self):
        with patch.dict('os.environ', {'NOTIFY_SOCKET': '/private/tmp/nonexistent-flare-notify-socket'}):
            with self.assertRaises(OSError):
                notify_healthy({'violations': []}, False)

    def test_physical_free_and_available_are_separate_gates(self):
        healthy = {'MemFree': 3 * GIB // 2, 'MemAvailable': 8 * GIB}
        self.assertEqual(violations({'head': healthy, 'worker': healthy}), [])
        self.assertEqual(violations({'head': dict(healthy, MemFree=GIB)}), ['head:MemFree'])
        self.assertEqual(violations({'worker': dict(healthy, MemAvailable=7 * GIB)}), ['worker:MemAvailable'])

    def test_missing_invalid_and_duplicate_observations_rejected(self):
        data = 'MemTotal: 100 kB\nMemFree: 20 kB\nMemAvailable: 80 kB\nSwapTotal: 10 kB\nSwapFree: 5 kB\n'
        self.assertEqual(memory(data)['MemAvailable'], 80 * 1024)
        for invalid in (data.replace('MemFree: 20 kB\n', ''), data + 'MemFree: 20 kB\n',
                        data.replace('20 kB', '-20 kB'), data.replace('80 kB', '80 MB'),
                        data.replace('80 kB', '120 kB'), data.replace('5 kB', '15 kB')):
            with self.assertRaises(ValueError):
                memory(invalid)

    def test_restoration_is_queued_in_its_own_unit(self):
        unit = 'b12x-flare-native-serve-restore-20261115T230000Z.service'
        with patch('flare_memory_watch.subprocess.run') as run:
            queue_restore(unit)
            self.assertEqual(run.call_args.args[0], ['systemctl', '--user', 'start', '--no-block', unit])
            for bad in ('vllm-b12x.service', unit + '; echo x', 'b12x-flare-anything.service'):
                with self.assertRaises(ValueError):
                    queue_restore(bad)
            self.assertEqual(run.call_count, 1)
