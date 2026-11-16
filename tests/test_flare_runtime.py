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
from flare_run import serving_command, serving_recipe
from flare_provenance import export_receipt


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
        (self.root/'local').mkdir()
        self.receipt = self.root/'local/export.json'
        self.plan = {'native_dense_activations': True, 'repository': self.recipe['model'],
            'revision': self.recipe['checkpoint_revision'], 'tensor_parallel': 2,
            'max_concurrency': 4, 'prefill_chunk': 4096, 'context_parallel': False,
            'language_model_only': True, 'speculation': {'draft_tokens': 3, 'adaptive': False}}
        self.receipt.write_text(json.dumps({'schema': 1, 'core_primary': str(self.core),
            'core_primary_sha256': self.state['core_primary_sha256'],
            'plan': self.plan, 'argv': ['--native-dense-activations'],
            'flare_revision': self.recipe['flare_revision'],
            'checkpoint_revision': self.recipe['checkpoint_revision']}))
        self.state.update(export_receipt=str(self.receipt),
                          export_receipt_sha256=hashlib.sha256(self.receipt.read_bytes()).hexdigest())

    def test_old_or_mismatched_export_rejected(self):
        old = {k:v for k,v in self.state.items() if not k.startswith('export_receipt')}
        with self.assertRaisesRegex(ValueError, 'provenance is missing'):
            serving_command(self.recipe, 0, old)
        with self.assertRaisesRegex(ValueError, 'activation option differs'):
            serving_command(dict(self.recipe, native_dense_activations=False), 1, self.state)
        data = json.loads(self.receipt.read_text())
        data['core_primary_sha256'] = '0'*64
        self.receipt.write_text(json.dumps(data))
        self.state['export_receipt_sha256'] = hashlib.sha256(self.receipt.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, 'different core'):
            serving_command(self.recipe, 0, self.state)

    def test_export_requires_resolved_plan_and_new_primary(self):
        log = self.root/'export.log'
        log.write_text(json.dumps({'plan': self.plan})+'\n'
                       +'Exported cache entry: '+str(self.core.parent)+'\n')
        command = ['ignition', 'export', '--native-dense-activations']
        receipt = export_receipt(self.recipe, command, log, set())
        self.assertEqual(receipt['core_primary_sha256'], self.state['core_primary_sha256'])
        with self.assertRaisesRegex(ValueError, 'new primary'):
            export_receipt(self.recipe, command, log, {self.core})
        with self.assertRaisesRegex(ValueError, 'argv differs'):
            export_receipt(self.recipe, ['ignition', 'export'], log, set())
        log.write_text('Exported cache entry: '+str(self.core.parent)+'\n')
        with self.assertRaisesRegex(ValueError, 'exactly one resolved plan'):
            export_receipt(self.recipe, command, log, set())

    def test_native_flag_on_export_only_and_strict_boolean(self):
        from flare_candidate import render
        self.assertIn('--native-dense-activations', render(self.recipe, 0)['prepare'])
        self.assertNotIn('--native-dense-activations', render(self.recipe, 1)['prepare'])
        self.assertNotIn('--native-dense-activations', render(self.recipe, 0)['serve'])
        self.assertNotIn('--native-dense-activations', render(dict(self.recipe, native_dense_activations=False), 0)['prepare'])
        for value in ('true', 1, None):
            with self.assertRaisesRegex(ValueError, 'must be a boolean'):
                render(dict(self.recipe, native_dense_activations=value), 0)

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

    def test_last_reserve_arm_changes_serving_only(self):
        from flare_candidate import render
        original = render(self.recipe, 0)
        self.assertEqual(serving_recipe(self.recipe), self.recipe)
        (self.root/'.env').write_text('# trial ledger\nFLARE_SERVE_RESERVE_GIB=4\nUNRELATED=ignored\nFLARE_SERVE_RESERVE_GIB=3\n')
        candidate = serving_recipe(self.recipe)
        rendered = render(candidate, 0)
        self.assertEqual(rendered['config_toml'], original['config_toml'])
        self.assertEqual(rendered['prepare'], original['prepare'])
        self.assertEqual(rendered['serve'][rendered['serve'].index('--memory-limit')+1], '-3G')
        self.assertNotIn('serve_reserve_gib', self.recipe)
        with (self.root/'.env').open('a') as f:
            f.write('FLARE_SERVE_RESERVE_GIB=4\n')
        reverted = render(serving_recipe(self.recipe), 0)
        self.assertEqual(reverted['serve'], original['serve'])

    def test_invalid_reserve_arm_is_not_evaluated(self):
        for value in ('0', '-3', '3; false', '$(false)', '3.5'):
            (self.root/'.env').write_text('FLARE_SERVE_RESERVE_GIB='+value+'\n')
            with self.assertRaisesRegex(ValueError, 'positive integer'):
                serving_recipe(self.recipe)

    def test_effective_assignment_can_correct_an_invalid_historical_arm(self):
        (self.root/'.env').write_text('FLARE_SERVE_RESERVE_GIB=$(false)\n'
            'FLARE_SCHEDULER_POLICY=invalid\nFLARE_NATIVE_ARM=invalid\n'
            'FLARE_SCHEDULER_TRACE=BAD.jsonl\nFLARE_SERVE_RESERVE_GIB=4\n'
            'FLARE_SCHEDULER_POLICY=balanced\nFLARE_NATIVE_ARM=upstream\n'
            'FLARE_SCHEDULER_TRACE=off\n')
        recipe = serving_recipe(self.recipe)
        self.assertEqual([recipe[k] for k in ('serve_reserve_gib','scheduler_policy','native_arm','scheduler_trace')],
                         [4,'balanced','upstream','off'])
        with (self.root/'.env').open('a') as file:
            file.write('FLARE_SCHEDULER_TRACE=BAD.jsonl\n')
        with self.assertRaisesRegex(ValueError,'local JSONL filename'):
            serving_recipe(self.recipe)

    def native_arm(self, trace=False):
        patch = self.root/'qualification/flare-prefill-latency.patch'
        patch.parent.mkdir()
        patch.write_bytes(b'host policy fixture')
        locks = {}
        for name in ('helios/Cargo.lock', 'flare-cli/Cargo.lock'):
            path = self.root/'upstream/flare'/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(name.encode())
            locks[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest = {'schema': 1, 'kind': 'prefill-latency',
            'flare_revision': self.recipe['flare_revision'],
            'patch_sha256': hashlib.sha256(patch.read_bytes()).hexdigest(),
            'binary_sha256': hashlib.sha256(b'native executable fixture').hexdigest(),
            'lock_sha256': locks}
        if trace:
            capture = patch.with_name('flare-scheduler-trace.patch')
            capture.write_bytes(b'trace fixture')
            manifest.update(trace_patch_sha256=hashlib.sha256(capture.read_bytes()).hexdigest(), trace_schema=1)
        data = json.dumps(manifest).encode()
        arm = hashlib.sha256(data).hexdigest()
        directory = self.root/'native'/arm
        directory.mkdir(parents=True)
        (directory/'manifest.json').write_bytes(data)
        (directory/'flare').write_bytes(b'native executable fixture')
        (self.root/'.env').write_text(f'FLARE_NATIVE_ARM={arm}\nFLARE_SCHEDULER_POLICY=latency\n')
        return directory

    def test_trace_is_explicit_head_only_and_cannot_overwrite(self):
        self.native_arm(trace=True)
        with (self.root/'.env').open('a') as f:
            f.write('FLARE_SCHEDULER_TRACE=probe.jsonl\n')
        recipe = serving_recipe(self.recipe)
        head = serving_command(recipe, 0, self.state)
        self.assertEqual(head[head.index('--scheduler-trace')+1], str(self.root/'local/probe.jsonl'))
        self.assertNotIn('--scheduler-trace', serving_command(recipe, 1, self.state))
        (self.root/'local/probe.jsonl').write_text('retained evidence')
        with self.assertRaisesRegex(ValueError, 'must not exist'):
            serving_command(recipe, 0, self.state)
        with (self.root/'.env').open('a') as f:
            f.write('FLARE_SCHEDULER_TRACE=off\n')
        self.assertNotIn('--scheduler-trace', serving_command(serving_recipe(self.recipe), 0, self.state))

    def test_trace_requires_verified_contract_and_rejects_path_escape(self):
        self.native_arm()
        with self.assertRaisesRegex(ValueError, 'lacks the qualified trace contract'):
            serving_command(dict(serving_recipe(self.recipe), scheduler_trace='probe.jsonl'), 0, self.state)
        for value in ('../escape.jsonl', '/tmp/probe.jsonl', '$(false).jsonl'):
            (self.root/'.env').write_text('FLARE_SCHEDULER_TRACE='+value+'\n')
            with self.assertRaisesRegex(ValueError, 'local JSONL filename'):
                serving_recipe(self.recipe)

    def test_trace_patch_mutation_rejected_even_with_capture_off(self):
        self.native_arm(trace=True)
        (self.root/'qualification/flare-scheduler-trace.patch').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'trace patch digest mismatch'):
            serving_command(serving_recipe(self.recipe), 1, self.state)

    def test_native_policy_arm_preserves_core_export_and_has_explicit_rollback(self):
        from flare_candidate import render
        original = render(self.recipe, 0)
        directory = self.native_arm()
        recipe = serving_recipe(self.recipe)
        for rank in (0, 1):
            cmd = serving_command(recipe, rank, self.state)
            self.assertEqual(cmd[0], str(directory/'flare'))
            self.assertEqual(cmd[cmd.index('--scheduler-policy')+1], 'latency')
            self.assertIn('--verify-weights', cmd)
        updated = render(recipe, 0)
        self.assertEqual(updated['prepare'], original['prepare'])
        self.assertEqual(updated['config_toml'], original['config_toml'])
        with (self.root/'.env').open('a') as f:
            f.write('FLARE_NATIVE_ARM=upstream\nFLARE_SCHEDULER_POLICY=balanced\n')
        reverted = serving_command(serving_recipe(self.recipe), 0, self.state)
        self.assertEqual(reverted[0], original['serve'][0])
        self.assertEqual(reverted[reverted.index('--scheduler-policy')+1], 'balanced')

    def test_native_arm_rejects_mutated_artifacts_and_symlinks(self):
        directory = self.native_arm()
        recipe = serving_recipe(self.recipe)
        for path in (directory/'manifest.json', directory/'flare',
                     self.root/'qualification/flare-prefill-latency.patch',
                     self.root/'upstream/flare/helios/Cargo.lock'):
            original = path.read_bytes()
            path.write_bytes(original + b'changed')
            with self.assertRaisesRegex(ValueError, 'mismatch'):
                serving_command(recipe, 0, self.state)
            path.write_bytes(original)
        binary = directory/'flare'
        outside = self.root/'outside-binary'
        binary.rename(outside)
        binary.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'immutable directory'):
            serving_command(recipe, 1, self.state)

    def test_invalid_native_arm_and_policy_are_rejected_without_evaluation(self):
        from flare_candidate import render
        for line in ('FLARE_NATIVE_ARM=../../b12x', 'FLARE_NATIVE_ARM=$(false)',
                     'FLARE_NATIVE_ARM='+'A'*64, 'FLARE_SCHEDULER_POLICY=latency; false'):
            (self.root/'.env').write_text(line+'\n')
            with self.assertRaises(ValueError):
                serving_recipe(self.recipe)
        with self.assertRaisesRegex(ValueError, 'verified native arm'):
            render(dict(self.recipe, scheduler_policy='latency'), 0)


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
