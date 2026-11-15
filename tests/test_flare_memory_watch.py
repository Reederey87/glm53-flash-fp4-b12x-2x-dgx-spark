from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from flare_memory_watch import GIB, memory, queue_restore, violations


class MemoryWatchTests(unittest.TestCase):
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
