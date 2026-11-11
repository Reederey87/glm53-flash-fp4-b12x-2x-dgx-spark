"""Compound evidence, peer deadlines and failure-position regressions."""
import copy
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import shutil
import time
import types
import unittest
from unittest.mock import patch
import pcp_native_receipt as R
from check_pcp_timer import budget_remaining
from run_pcp_micro import native_suite,transaction,NODES
import test_native_ownership as N
import test_pcp_bound as P
import check_pcp_native_cuda as wrapper


class Deadlines(unittest.TestCase):
    def test_actual_300_and_600_deadlines(self):
        for duration,budget in ((300,240),(300,180),(600,540),(600,180)):
            self.assertEqual(budget_remaining(1_000_000,(duration+1)*1_000_000,2_000_000,duration,budget),duration-1)

    def test_caller_cannot_turn_300_timer_into_600(self):
        with self.assertRaisesRegex(ValueError,'actual rollback deadline'):
            budget_remaining(1_000_000,301_000_000,2_000_000,600,540)
        for entered,end,now in ((0,600_000_000,1),(1,600_000_001,600_000_000),(10,600_000_010,1)):
            with self.assertRaises(ValueError):budget_remaining(entered,end,now,600,180)


class Suite(unittest.TestCase):
    def plan(self):return [dict(node=n,spelling=s,run_id=f'{i:032x}') for i,(n,s) in enumerate(( (n,s) for n in NODES for s in ('unindexed','indexed')))]

    def test_fixed_order_checks_both_peers_and_completes(self):
        plan=self.plan();calls=[]
        proofs=native_suite(plan,lambda peer,r:calls.append(('budget',peer,r['run_id'])),
            lambda r:calls.append(('run',r['node'],r['spelling'])) or 'log',lambda log,r:{'ok':True})
        self.assertEqual(len(proofs),4);self.assertEqual(len([c for c in calls if c[0]=='budget']),8)
        self.assertEqual([c[1:] for c in calls if c[0]=='run'],[(r['node'],r['spelling']) for r in plan])

    def test_failure_at_each_position_skips_rest_and_restores_both(self):
        for position in range(4):
            plan=self.plan();calls=[];restores=[]
            def run(row):
                calls.append(row)
                if row is plan[position]:raise RuntimeError('child failed after valid-looking summary')
                return 'log'
            with self.assertRaises(RuntimeError):
                transaction(lambda:native_suite(plan,lambda *a:None,run,lambda *a:{}),restores.append,lambda n:None,lambda n:self.fail('cancel after failure'))
            self.assertEqual(len(calls),position+1);self.assertEqual(restores,list(NODES))

    def test_peer_exhaustion_prevents_probe(self):
        calls=[]
        def budget(peer,row):
            if peer=='worker':raise ValueError('peer deadline exhausted')
        with self.assertRaises(ValueError):native_suite(self.plan(),budget,lambda r:calls.append(r),lambda *a:{})
        self.assertEqual(calls,[])

    def test_bad_plan_or_duplicate_id_fails_before_any_work(self):
        for mode in ('order','duplicate'):
            plan=self.plan()
            if mode=='order':plan.reverse()
            else:plan[1]['run_id']=plan[0]['run_id']
            with self.assertRaises(ValueError):native_suite(plan,lambda *a:self.fail('budget ran'),lambda *a:None,lambda *a:None)


class CompoundReceipt(unittest.TestCase):
    def fixture(self):
        _,lines,_=N.Receipts().fixture_log();kernel=P.Policy().fixture()
        kernel['settings_read_only']['percpu_pagelist_high_fraction']='512'
        begin=dict(pid=1,utc_ns=1,kernel=kernel,allocator_state=copy.deepcopy(R.EXPECTED_STATE),device_spelling='unindexed',node='head',run_id='a'*32,
            parent_sha256=R.PARENT_SHA,scope='model-free-entry-not-model-profile')
        end=dict(pid=1,utc_ns=30,kernel=copy.deepcopy(kernel),allocator_state=copy.deepcopy(R.EXPECTED_STATE),device_spelling='unindexed',node='head',run_id='a'*32,
            parent_sha256=R.PARENT_SHA,checkpoint_loaded=False,server_loaded=False,checkpoint_deployment_cleared=False)
        summary=dict(device='cuda',pid=1,terminal_collector=True,common_pinned_return_completed=True,
            prepared_b12x_replays=3,pinned_copy_replays=3,pointers_preserved=True,compiler_and_loader_forbidden=True,
            checkpoint_loaded=False,admission_stub_not_model_profile=True,server_loaded=False)
        return ['B12X_PCP_NATIVE_BEGIN '+json.dumps(begin),*lines,json.dumps(summary),'B12X_PCP_NATIVE_END '+json.dumps(end)]

    def check(self,lines):
        with patch.object(R,'WORKER','w'),patch.object(R,'HELPER','h'),patch.object(R,'COLLECTOR','m'),patch.object(Path,'read_text',return_value='0-19\n'):
            return R.validate('\n'.join(lines),'unindexed','head','a'*32)

    def test_complete_compound_does_not_clear_model(self):
        proof=self.check(self.fixture());self.assertTrue(proof['compound_micro_qualified'])
        self.assertFalse(proof['checkpoint_deployment_cleared']);self.assertEqual(proof['pinned_return']['idle_returned_bytes'],512*1024**2)

    def test_wrong_invocation_source_pid_device_rejects(self):
        for field,value in (('run_id','b'*32),('node','worker'),('parent_sha256','bad'),('pid',3),('device_spelling','indexed')):
            lines=self.fixture();row=json.loads(lines[0].split(' ',1)[1]);row[field]=value;lines[0]='B12X_PCP_NATIVE_BEGIN '+json.dumps(row)
            with self.subTest(field=field),self.assertRaises(ValueError):self.check(lines)
        lines=self.fixture();summary=json.loads(lines[-2]);summary['device']='cuda:0';lines[-2]=json.dumps(summary)
        with self.assertRaises(ValueError):self.check(lines)

    def test_summary_without_normal_teardown_marker_rejects(self):
        with self.assertRaises(ValueError):self.check(self.fixture()[:-1])

    def test_post_parent_allocator_drift_rejects_receipt(self):
        lines=self.fixture();row=json.loads(lines[-1].split(' ',1)[1]);row['allocator_state']['effective_settings']='changed'
        lines[-1]='B12X_PCP_NATIVE_END '+json.dumps(row)
        with self.assertRaises(ValueError):self.check(lines)

    def test_missing_duplicate_chunks_and_failed_physical_gate_reject(self):
        for mode in ('missing','duplicate','physical'):
            lines=self.fixture();index=next(i for i,l in enumerate(lines) if l.startswith('B12X_NATIVE_OWNERS '))
            if mode=='missing':lines.pop(index)
            elif mode=='duplicate':lines.insert(index,lines[index])
            else:
                index=next(i for i,l in enumerate(lines) if l.startswith('B12X_PINNED_RETURN ') and '"phase": "after"' in l)
                row=json.loads(lines[index].split(' ',1)[1]);row['host']['MemAvailable']=8*1024**3;lines[index]='B12X_PINNED_RETURN '+json.dumps(row)
            with self.subTest(mode=mode),self.assertRaises(ValueError):self.check(lines)


class Wrapper(unittest.TestCase):
    def test_post_parent_allocator_drift_has_no_END(self):
        torch=types.SimpleNamespace(cuda=types.SimpleNamespace(init=lambda:None))
        parent=types.SimpleNamespace(torch=torch,main=lambda:None)
        with patch.dict(sys.modules,{'check_native_ownership_cuda':parent}),patch.object(wrapper,'snapshot',return_value={}),\
             patch.object(wrapper,'validate_policy',side_effect=lambda r,f:r),patch.object(wrapper,'allocator_state',side_effect=[wrapper.EXPECTED_STATE,ValueError('post drift')]),\
             patch.dict(os.environ,PYTORCH_CUDA_ALLOC_CONF='',PYTORCH_ALLOC_CONF='',PYTORCH_HIP_ALLOC_CONF=''),\
             patch.object(sys,'argv',['probe','--device-spelling','unindexed','--node','head','--run-id','a'*32]),contextlib.redirect_stdout(io.StringIO()) as out:
            with self.assertRaisesRegex(ValueError,'post drift'):wrapper.main()
        self.assertNotIn('B12X_PCP_NATIVE_END ',out.getvalue())
    def test_parent_teardown_failure_has_no_END_marker(self):
        torch=types.SimpleNamespace(version=types.SimpleNamespace(git_version='cf30153c4c131c8164ee7798e5022d810682e2cb'),
            cuda=types.SimpleNamespace(init=lambda:None,current_device=lambda:0,memory=types.SimpleNamespace(get_allocator_backend=lambda:'native')),
            _C=types.SimpleNamespace(_accelerator_getAllocatorSettings=lambda:''))
        def parent_main():print('{"terminal_collector":true}');raise RuntimeError('teardown failed')
        parent=types.SimpleNamespace(torch=torch,main=parent_main)
        with patch.dict(sys.modules,{'check_native_ownership_cuda':parent}),patch.object(wrapper,'snapshot',return_value={}),\
             patch.object(wrapper,'validate_policy',side_effect=lambda r,f:r),patch.dict(os.environ,PYTORCH_CUDA_ALLOC_CONF='',PYTORCH_ALLOC_CONF='',PYTORCH_HIP_ALLOC_CONF=''),\
             patch.object(sys,'argv',['probe','--device-spelling','unindexed','--node','head','--run-id','a'*32]),contextlib.redirect_stdout(io.StringIO()) as out:
            with self.assertRaisesRegex(RuntimeError,'teardown failed'):wrapper.main()
        self.assertIn('B12X_PCP_NATIVE_BEGIN ',out.getvalue());self.assertNotIn('B12X_PCP_NATIVE_END ',out.getvalue())


class Cleanup(unittest.TestCase):
    def test_owned_GPU_removed_before_policy_restore_or_failure_stops_restore(self):
        source=Path('mods/pcp-bound/rollback-native.sh').read_text()
        for fail in (False,True):
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory);scripts=root/'mods/pcp-bound';scripts.mkdir(parents=True);bin=root/'bin';bin.mkdir()
                (scripts/'rollback-native.sh').write_text(source)
                (scripts/'rollback.sh').write_text('echo RESTORE >> "$PCP_TEST_LOG"\n')
                (root/'.pcp-lease').write_text('armed');(root/'.pcp-lock').touch();(root/'active').touch()
                (bin/'timeout').write_text('#!/bin/sh\ncase "$1" in --kill-after=*) shift ;; esac\nshift\nexec "$@"\n')
                (bin/'flock').write_text('#!/bin/sh\nshift 4\nexec "$@"\n')
                (bin/'docker').write_text('''#!/bin/sh
set -eu
case "$1" in
 ps) if test -f "$PCP_TEST_ROOT/active"; then echo aaaaaaaaaaaa; fi ;;
 rm) test "$(cat "$PCP_TEST_ROOT/.pcp-lease")" = closed
     if test "$PCP_TEST_FAIL" = 1; then exit 1; fi
     echo REMOVE >> "$PCP_TEST_LOG"; rm "$PCP_TEST_ROOT/active" ;;
 *) exit 66 ;;
esac
''')
                for f in bin.iterdir():f.chmod(0o755)
                env=dict(os.environ,PATH=str(bin)+':'+os.environ['PATH'],PCP_TEST_ROOT=str(root),PCP_TEST_LOG=str(root/'log'),PCP_TEST_FAIL=str(int(fail)))
                result=subprocess.run(['bash',str(scripts/'rollback-native.sh')],env=env,capture_output=True)
                self.assertEqual((root/'.pcp-lease').read_text().strip(),'closed')
                if fail:self.assertNotEqual(result.returncode,0);self.assertFalse((root/'log').exists())
                else:self.assertEqual(result.returncode,0,result.stderr);self.assertEqual((root/'log').read_text(),'REMOVE\nRESTORE\n')


class LaunchRace(unittest.TestCase):
    def test_paused_start_cannot_escape_rollback_and_closed_lease_blocks_create(self):
        gpu=Path('mods/pcp-bound/gpu-native.sh').read_text();rollback=Path('mods/pcp-bound/rollback-native.sh').read_text()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);scripts=root/'mods/pcp-bound';scripts.mkdir(parents=True);bin=root/'bin';bin.mkdir()
            gpu=gpu.replace('/proc/sys/vm/percpu_pagelist_high_fraction',str(root/'policy'))
            (scripts/'gpu-native.sh').write_text(gpu);(scripts/'rollback-native.sh').write_text(rollback)
            (scripts/'rollback.sh').write_text('printf "0\\n" > "$PCP_TEST_ROOT/policy"\necho RESTORE >> "$PCP_TEST_ROOT/log"\n')
            (root/'policy').write_text('512');(root/'.pcp-lease').write_text('armed');(root/'.pcp-lock').touch()
            (bin/'timeout').write_text('#!/bin/sh\ncase "$1" in --kill-after=*) shift ;; esac\ncase "$1" in --signal=*) shift; shift ;; esac\nshift\nexec "$@"\n')
            (bin/'sha256sum').write_text('#!/bin/sh\nexit 0\n');(bin/'systemctl').write_text('#!/bin/sh\necho 0\n')
            lock=root/'lock.py';lock.write_text('''import fcntl,os,subprocess,sys
a=sys.argv[1:]
if a[0]=='-u':fcntl.flock(int(a[1]),fcntl.LOCK_UN);sys.exit(0)
target=a[3];fd=int(target) if target.isdecimal() else os.open(target,os.O_RDWR)
fcntl.flock(fd,fcntl.LOCK_EX)
if len(a)>4:sys.exit(subprocess.run(a[4:],pass_fds=(fd,)).returncode)
''')
            (bin/'flock').write_text('#!/bin/sh\nexec "$PCP_TEST_UV" run --offline --no-project --python "$PCP_TEST_PYTHON" "$PCP_TEST_LOCK" "$@"\n')
            (bin/'docker').write_text('''#!/bin/sh
set -eu
case "$1" in
 image) echo sha256:3b5da79c42ed4204440cfb07c6de1eba46441d5cba6b57d5428d44e60c10d0ed ;;
 ps) if test "$2" = -aq && test -f "$PCP_TEST_ROOT/container"; then printf '%064d\\n' 1; fi ;;
 create) touch "$PCP_TEST_ROOT/container"; echo CREATE >> "$PCP_TEST_ROOT/log"; printf '%064d\\n' 1 ;;
 start) touch "$PCP_TEST_ROOT/start-ready"
        while ! test -f "$PCP_TEST_ROOT/release"; do sleep .01; done
        test -f "$PCP_TEST_ROOT/container" || exit 44
        echo GPU_STARTED >> "$PCP_TEST_ROOT/log"; rm "$PCP_TEST_ROOT/container" ;;
 rm) rm -f "$PCP_TEST_ROOT/container"; echo REMOVE >> "$PCP_TEST_ROOT/log" ;;
 *) exit 66 ;;
esac
''')
            for f in bin.iterdir():f.chmod(0o755)
            env=dict(os.environ,PATH=str(bin)+':'+os.environ['PATH'],PCP_TEST_ROOT=str(root),PCP_TEST_UV=shutil.which('uv'),PCP_TEST_PYTHON=sys.executable,PCP_TEST_LOCK=str(lock))
            with subprocess.Popen(['bash',str(scripts/'gpu-native.sh'),'unindexed','a'*32,'head'],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE) as child:
                try:
                    deadline=time.monotonic()+8
                    while not (root/'start-ready').exists() and child.poll() is None and time.monotonic()<deadline:time.sleep(.01)
                    self.assertTrue((root/'start-ready').exists(),'launcher failed to reach paused start')
                    result=subprocess.run(['bash',str(scripts/'rollback-native.sh')],env=env,capture_output=True,timeout=8)
                    self.assertEqual(result.returncode,0,result.stderr)
                    (root/'release').touch();stdout,stderr=child.communicate(timeout=8)
                    self.assertNotEqual(child.returncode,0,(stdout,stderr));self.assertNotIn('GPU_STARTED',(root/'log').read_text())
                    self.assertEqual((root/'log').read_text(),'CREATE\nREMOVE\nRESTORE\n')
                finally:
                    (root/'release').touch()
                    if child.poll() is None:child.kill();child.communicate()
            before=(root/'log').read_text()
            result=subprocess.run(['bash',str(scripts/'gpu-native.sh'),'unindexed','b'*32,'head'],env=env,capture_output=True,timeout=8)
            self.assertNotEqual(result.returncode,0);self.assertEqual((root/'log').read_text(),before)


if __name__=='__main__':unittest.main()
