import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import signal
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import flare_run
from flare_candidate import RECIPE, load_recipe
from flare_run import serving_command


class RuntimeContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.recipe = load_recipe(RECIPE)
        self.recipe['runtime_root'] = str(self.root)
        (self.root/'cores').mkdir()
        self.core = self.root/'cores/model.safetensors'
        self.core.write_bytes(b'fixture primary')
        self.key = bytes(range(32))
        self.profile = self.root/'development-publisher.json'
        self.profile.write_text(json.dumps([{'namespace': 'local-development', 'public_key': list(self.key)}]))
        self.state = {'publisher_profile_sha256': hashlib.sha256(self.profile.read_bytes()).hexdigest(),
                      'key_fingerprint': hashlib.sha256(self.key).hexdigest(),
                      'core_primary': str(self.core),
                      'core_primary_sha256': hashlib.sha256(self.core.read_bytes()).hexdigest()}

    def test_exact_acceptance_and_isolated_endpoint(self):
        cmd = serving_command(self.recipe, 0, self.state)
        self.assertEqual(cmd[cmd.index('--dangerously-approve-key')+1], self.state['key_fingerprint'])
        self.assertEqual(cmd[cmd.index('--dangerously-accept-publisher')+1], 'local-development')
        self.assertIn('127.0.0.1', cmd)
        self.assertIn('8001', cmd)
        self.assertIn('--verify-weights', cmd)
        self.assertNotIn(str(self.core), serving_command(self.recipe, 1, self.state))

    def test_changed_profile_or_primary_rejected(self):
        self.core.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'primary changed'):
            serving_command(self.recipe, 0, self.state)
        self.profile.write_text('[]')
        with self.assertRaisesRegex(ValueError, 'profile changed'):
            serving_command(self.recipe, 1, self.state)

    def test_core_escape_rejected(self):
        self.state['core_primary'] = str(self.root/'outside.safetensors')
        with self.assertRaisesRegex(ValueError, 'isolated candidate'):
            serving_command(self.recipe, 0, self.state)

    def test_fingerprint_rejected(self):
        self.state['key_fingerprint'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'fingerprint mismatch'):
            serving_command(self.recipe, 1, self.state)


class ShutdownTests(unittest.TestCase):
    def run_peer_failure(self, *, shutdown=False, timeout=False):
        handlers = {}
        recipe = load_recipe(RECIPE)
        child = Mock(returncode=None)
        child.poll.side_effect = lambda: child.returncode
        child.terminate.side_effect = lambda: setattr(child, 'returncode', -signal.SIGTERM)

        def run(command, **kwargs):
            if '--property=ActiveState' in command:
                if shutdown:
                    handlers[signal.SIGTERM](signal.SIGTERM, None)
                if timeout:
                    raise subprocess.TimeoutExpired(command, 20)
                return subprocess.CompletedProcess(command, 255, '', 'connection closed')
            return subprocess.CompletedProcess(command, 0, '', '')

        with patch.object(sys, 'argv', ['flare_run.py', 'serve', '0']), \
             patch.object(flare_run, 'load_recipe', return_value=recipe), \
             patch.object(flare_run, 'inspect_host', return_value={}), \
             patch.object(flare_run, 'blockers', return_value=[]), \
             patch.object(flare_run, 'serving_command', return_value=['fake-native-server']), \
             patch.object(Path, 'read_text', return_value='{}'), \
             patch.object(subprocess, 'check_output', return_value=''), \
             patch.object(subprocess, 'run', side_effect=run), \
             patch.object(subprocess, 'Popen', return_value=child), \
             patch.object(signal, 'signal', side_effect=lambda signum, fn: handlers.update({signum: fn})):
            return flare_run.main()

    def test_sigterm_during_peer_check_is_clean_shutdown(self):
        self.assertEqual(self.run_peer_failure(shutdown=True), 0)
        self.assertEqual(self.run_peer_failure(shutdown=True, timeout=True), 0)

    def test_unexpected_peer_failure_remains_fatal(self):
        with self.assertRaisesRegex(RuntimeError, 'peer failed'):
            self.run_peer_failure()
        with self.assertRaises(subprocess.TimeoutExpired):
            self.run_peer_failure(timeout=True)


if __name__ == '__main__':
    unittest.main()
