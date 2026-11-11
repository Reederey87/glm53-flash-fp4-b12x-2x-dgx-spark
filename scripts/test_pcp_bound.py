"""Rollback and sealed observational-evidence regressions; CPU only."""
import contextlib
import copy
import io
import json
import re
import os
import subprocess
import tempfile
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
import check_pcp_bound_cuda as probe
import pcp_bound_snapshot as policy
import pcp_micro_receipt as receipt
from run_pcp_micro import transaction,NODES,cancel_command


class Transaction(unittest.TestCase):
    def test_unloaded_transient_service_cancellation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);stub=root/'systemctl';log=root/'log'
            stub.write_text('#!/bin/sh\necho "$*" >> "$PCP_TEST_LOG"\ncase "$*" in *LoadState*) echo "$PCP_TEST_STATE" ;; esac\n');stub.chmod(0o755)
            for state,expected_stops,code in (('not-found',1,0),('loaded',2,0),('error',1,1)):
                log.write_text('')
                env=dict(os.environ,PATH=str(root)+':'+os.environ['PATH'],PCP_TEST_LOG=str(log),PCP_TEST_STATE=state)
                result=subprocess.run(['sh','-c',cancel_command('test')],env=env,capture_output=True)
                self.assertEqual(result.returncode,code);self.assertEqual(log.read_text().count('--user stop'),expected_stops)
    def run_case(self,fail=None):
        calls=[]
        def action(name,node=None):
            key=name if node is None else name+'-'+node;calls.append(key)
            if key==fail:raise RuntimeError(key)
            return 'done'
        result=transaction(lambda:action('perform'),lambda n:action('restore',n),
            lambda n:action('verify',n),lambda n:action('cancel',n))
        return result,calls

    def test_success_restores_both_before_cancelling(self):
        result,calls=self.run_case();self.assertEqual(result,'done')
        self.assertEqual(calls,['perform','restore-head','verify-head','restore-worker','verify-worker','cancel-head','cancel-worker'])

    def test_failure_and_interrupt_restore_both_and_retain_timers(self):
        for error in (RuntimeError('partial apply'),KeyboardInterrupt()):
            calls=[]
            def fail():raise error
            with self.assertRaises(type(error)):
                transaction(fail,lambda n:calls.append('restore-'+n),lambda n:calls.append('verify-'+n),lambda n:calls.append('cancel-'+n))
            self.assertEqual(calls,['restore-head','verify-head','restore-worker','verify-worker'])

    def test_each_restore_verify_failure_attempts_other_node_no_cancel(self):
        for kind in ('restore','verify'):
            for node in NODES:
                calls=[]
                def act(k,n):
                    calls.append((k,n))
                    if (k,n)==(kind,node):raise RuntimeError('injected')
                with self.assertRaisesRegex(RuntimeError,'unverified'):
                    transaction(lambda:None,lambda n:act('restore',n),lambda n:act('verify',n),lambda n:act('cancel',n))
                self.assertIn(('restore','worker'),calls);self.assertFalse(any(k=='cancel' for k,n in calls))

    def test_cancel_failure_still_attempts_other_node(self):
        calls=[]
        def cancel(n):
            calls.append(n)
            if n=='head':raise RuntimeError('cancel')
        with self.assertRaisesRegex(RuntimeError,'unverified'):transaction(lambda:None,lambda n:None,lambda n:None,cancel)
        self.assertEqual(calls,list(NODES))


class Policy(unittest.TestCase):
    def fixture(self):
        r=json.loads(Path('receipts/kernel-counter-audit/head-schema.json').read_text())
        for z in r['zones']:
            for c in z['cpus']:
                c['high_min']=c['high_max']=max(z['managed_pages']//512//20,4*c['batch'])
        return r

    def test_bounds_accept_stale_current_high_and_count(self):
        row=self.fixture()
        with patch.object(Path,'read_text',return_value='0-19\n'):
            self.assertIsNotNone(policy.validate(row,512))

    def test_activation_control_changes_fail(self):
        for key in ('batch','high_min','high_max'):
            r=self.fixture();r['zones'][0]['cpus'][0][key]+=1
            with patch.object(Path,'read_text',return_value='0-19\n'):
                with self.assertRaises(ValueError):policy.validate(r,512)
        r=self.fixture();r['page_size']=65536
        with patch.object(Path,'read_text',return_value='0-19\n'):
            with self.assertRaises(ValueError):policy.validate(r,512)


class Wrapper(unittest.TestCase):
    def run_fake(self,phases=None,fixtures=1):
        torch=types.SimpleNamespace(uint8='uint8',ones=lambda *a,**k:types.SimpleNamespace(numel=lambda:512*1024**2,element_size=lambda:1))
        parent=types.SimpleNamespace(torch=torch,sample=lambda phase:{'phase':phase})
        def main():
            for p in phases or ('before-fixture','resident-fixture','cached-before-helper','after-helper-or-exception'):parent.sample(p)
            for _ in range(fixtures):torch.ones(512*1024**2,dtype=torch.uint8,pin_memory=True)
        parent.main=main
        with patch.dict(sys.modules,{'check_host_register_memory_cuda':parent}),patch.object(probe.counters,'snapshot',return_value={}),\
             patch.object(sys,'argv',['probe','--fraction','512']),contextlib.redirect_stdout(io.StringIO()) as output:
            probe.main()
        return json.loads(output.getvalue().split(' ',1)[1])

    def test_complete_marker_keeps_checkpoint_false(self):
        r=self.run_fake();self.assertEqual(r['fraction'],512);self.assertFalse(r['checkpoint_deployment_cleared'])

    def test_missing_phase_or_fixture_rejects(self):
        for phases,fixtures in ((['before-fixture'],1),(None,0),(None,2)):
            with self.assertRaises(ValueError):self.run_fake(phases,fixtures)


class Lease(unittest.TestCase):
    def test_closed_lease_blocks_delayed_apply_and_restore_is_idempotent(self):
        text=Path('mods/pcp-bound/knob.sh').read_text()
        body=re.search(r"'(set -eu\n.*?)' sh",text,re.S)[1]
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name,value in (('knob','0'),('lease','armed')):(root/name).write_text(value)
            body=body.replace('/knob',str(root/'knob')).replace('/lease',str(root/'lease'))
            def run(a,b):return subprocess.run(['sh','-c',body,'sh',a,b],capture_output=True).returncode
            self.assertEqual(run('0','512'),0);self.assertEqual((root/'knob').read_text().strip(),'512')
            self.assertEqual(run('512','0'),0);self.assertEqual(run('512','0'),0)
            self.assertNotEqual(run('0','512'),0);self.assertEqual((root/'knob').read_text().strip(),'0')
            (root/'knob').write_text('256');self.assertNotEqual(run('512','0'),0)
            self.assertEqual((root/'knob').read_text(),'256')


class Receipt(unittest.TestCase):
    def fixture(self):
        log=Path('receipts/host-register/predeploy/head-default.log').read_text()
        parent=json.loads(next(l.split(' ',1)[1] for l in log.splitlines() if l.startswith('B12X_HOST_REGISTER_MEMORY ')))
        kernel=json.loads(Path('receipts/kernel-counter-audit/head-schema.json').read_text())
        result=dict(fraction=0,source_parents=probe.EXPECTED,checkpoint_deployment_cleared=False,
            checkpoint_loaded=False,server_loaded=False,fixture_allocation=dict(bytes=512*1024**2,begin_ns=0,end_ns=1),
            bundles=[dict(phase=r['phase'],process_sample=r,kernel=copy.deepcopy(kernel)) for r in parent['rows']])
        raw=[l for l in log.splitlines() if l.startswith('B12X_PINNED_RETURN ')]
        return parent,result,raw

    def log(self,p,r,raw):return '\n'.join([*raw,'B12X_HOST_REGISTER_MEMORY '+json.dumps(p),'B12X_PCP_MICRO '+json.dumps(r)])

    def test_preserves_failed_physical_gate(self):
        p,r,raw=self.fixture()
        with patch.object(Path,'read_text',return_value='0-19\n'):
            out=receipt.validate(self.log(p,r,raw),0)
        self.assertFalse(out['micro_qualified']);self.assertFalse(out['checkpoint_deployment_cleared'])

    def test_forged_success_or_bad_live_evidence_rejected(self):
        for key in ('helper_gate_passed','live_state_unchanged'):
            p,r,raw=self.fixture();p[key]=not p[key]
            with patch.object(Path,'read_text',return_value='0-19\n'):
                with self.assertRaises(ValueError):receipt.validate(self.log(p,r,raw),0)
        p,r,raw=self.fixture();r['checkpoint_deployment_cleared']=True
        with self.assertRaises(ValueError):receipt.validate(self.log(p,r,raw),0)


if __name__=='__main__':unittest.main()
