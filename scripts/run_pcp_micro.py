"""Head-side temporary both-node transaction; timers independently roll back."""
import argparse
from datetime import datetime,timezone
from pathlib import Path
import json
import os
import re
import shlex
import signal
import secrets
import subprocess

NODES=('head','worker')


def native_suite(plan,budget,run,validate):
    expected=[(n,s) for n in NODES for s in ('unindexed','indexed')]
    if [(r['node'],r['spelling']) for r in plan]!=expected:
        raise ValueError('compound probe order/coverage changed')
    ids=[r['run_id'] for r in plan]
    if len(set(ids))!=4 or any(not re.fullmatch('[0-9a-f]{32}',v) for v in ids):raise ValueError('invalid compound invocation plan')
    proofs={}
    for invocation in plan:
        for peer in NODES:budget(peer,invocation)
        log=run(invocation)
        proofs[invocation['node']+'-'+invocation['spelling']]=validate(log,invocation)
    return proofs


def ledger_command(node,label,kind='micro'):
    if kind not in ('micro','native'):raise ValueError('unregistered trial kind')
    ledger='/home/nvidia/b12x/.env';q=shlex.quote
    if node=='worker':return 'test ! -e '+q(ledger)+'\necho "Worker has no b12x env; head owns launch ledger"\n'
    if node!='head':raise ValueError('unknown node')
    backup=ledger+'.bak-pcp-bound-'+label
    return ('test -f '+q(ledger)+'\ntest ! -e '+q(backup)+'\ncp -n '+q(ledger)+' '+q(backup)+'\nsha256sum '+q(backup)+
        '\nprintf %s '+q('# PCP '+kind+' '+label+' policy0->512; unchanged model off,17GKV,2GiBfloor,minfree; rollback0; gate docs/gates/pcp-bound-'+kind+'.md\n')+' >> '+q(ledger)+'\n')


def with_bookkeeping(work,bookkeep):
    primary=None
    try:return work()
    except BaseException as error:primary=error;raise
    finally:
        try:bookkeep()
        except BaseException as error:
            if primary is not None:print('Bookkeeping failed separately: '+repr(error),file=__import__('sys').stderr)
            else:raise RuntimeError('bookkeeping failed; policy restoration verified') from error


def cancel_command(timer):
    q=shlex.quote
    return ('set -eu\nsystemctl --user stop '+q(timer+'.timer')+'\n'
        'state=$(systemctl --user show '+q(timer+'.service')+' -p LoadState --value)\n'
        'case "$state" in loaded) systemctl --user stop '+q(timer+'.service')+' ;; '
        'not-found) ;; *) echo "Unexpected rollback-service load state: $state" >&2; exit 1 ;; esac\n')


def transaction(perform,restore,verify,cancel):
    """Always attempt both restores; keep timers on any unverified restoration."""
    completed=False
    try:
        result=perform();completed=True;return result
    finally:
        errors=[]
        for node in NODES:
            try:restore(node);verify(node)
            except BaseException as error:errors.append((node,error))
        if not errors and completed:
            for node in NODES:
                try:cancel(node)
                except BaseException as error:errors.append((node,error))
        if errors:raise RuntimeError('rollback/cancellation unverified; independent timers retained: '+str(errors))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true',required=True)
    parser.add_argument('--kind',choices=('micro','native'),default='micro');args=parser.parse_args()
    kind=args.kind;duration=300 if kind=='micro' else 600
    def interrupted(signum,frame):raise KeyboardInterrupt('signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGHUP,interrupted)
    root=Path(__file__).resolve().parents[1]
    if not str(root).startswith('/home/nvidia/b12x-staging/pcp-bound-'):raise ValueError('inactive staging tree required')
    if root.stat().st_uid!=os.getuid() or root.stat().st_mode&0o077:raise ValueError('private owned staging tree required')
    label=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    prefix='pcp-bound-' if kind=='micro' else 'pcp-native-'
    out=Path('/home/nvidia/b12x/local')/(prefix+label);out.mkdir(exist_ok=False)
    plan=[dict(node=n,spelling=s,run_id=secrets.token_hex(16)) for n in NODES for s in ('unindexed','indexed')] if kind=='native' else None
    if plan is not None:(out/'probe-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    timer='b12x-pcp512-rollback-'+label.lower();q=shlex.quote
    rollback=root/('mods/pcp-bound/rollback.sh' if kind=='micro' else 'mods/pcp-bound/rollback-native.sh')
    def execute(node,key,script):
        command=['bash','-se'] if node=='head' else ['ssh','nvidia@192.168.177.11','bash','-se']
        with (out/(node+'-'+key+'.log')).open('w') as log:
            result=subprocess.run(command,input=script,text=True,stdout=log,stderr=subprocess.STDOUT,timeout=100)
        if result.returncode:raise RuntimeError(node+' '+key+' failed; see '+str(out))
    def checked(node,key,script):
        execute(node,key,'set -euo pipefail\ncd '+q(str(root))+'\nsha256sum -c .pcp-frozen.sha256\n'+script)
    def snapshot(node,key,fraction):
        checked(node,key,'/home/nvidia/.local/bin/uv run --offline --no-project --python /usr/bin/python3 scripts/pcp_bound_snapshot.py '+str(fraction)+'\n')
    def restore(node):
        # Rollback must not depend on source-manifest validity or a GPU lock.
        execute(node,'restore','set -eu\nbash '+q(str(rollback))+'\n')
    verified=set()
    def verify(node):
        snapshot(node,'restored',0)
        execute(node,'no-containers','test -z "$(docker ps -q)"\n')
        verified.add(node)
    def bookkeep():
        status='both policies verified0' if verified==set(NODES) else 'restoration unverified'
        execute('head','ledger-outcome','printf %s '+q('# PCP '+kind+' '+label+' ended; '+status+'; see local/'+prefix+label+'/ receipts; no adoption\n')+' >> /home/nvidia/b12x/.env\n')
    def cancel(node):execute(node,'timer-cancel',cancel_command(timer))
    def perform():
        for node in NODES:
            checked(node,'preflight','''test -z "$(docker ps -q)"
test "$(stat -c %a .)" = 700
test "$(stat -c %u .)" = "$(id -u)"
test "$(systemctl --user show vllm-b12x.service -p MainPID --value)" = 0
! systemctl --user is-active --quiet vllm-b12x-watchdog.timer
! systemctl --user is-active --quiet vllm-b12x-tailscale.service
''')
            snapshot(node,'before',0)
            checked(node,'ledger',ledger_command(node,label,kind))
        if kind=='micro':
            for node in NODES:
                checked(node,'A','bash mods/pcp-bound/gpu-node.sh 0\n')
                subprocess.run(['/home/nvidia/.local/bin/uv','run','--offline','--no-project','--python','/usr/bin/python3',str(root/'scripts/pcp_micro_receipt.py'),'check',str(out/(node+'-A.log')),'0'],check=True,timeout=10)
        for node in NODES:
            checked(node,'timer-arm','test ! -e .pcp-lease\nprintf "armed\\n" > .pcp-lease\ntouch .pcp-lock\nchmod 666 .pcp-lease .pcp-lock\nsystemd-run --user --unit='+q(timer)+' --on-active='+str(duration)+'s --timer-property=AccuracySec=1s --property=Restart=on-failure --property=RestartSec=5s --property=StartLimitIntervalSec=0 /bin/bash '+q(str(rollback))+'\nsystemctl --user is-active --quiet '+q(timer+'.timer')+'\n')
        for node in NODES:checked(node,'apply','/home/nvidia/.local/bin/uv run --offline --no-project --python /usr/bin/python3 scripts/check_pcp_timer.py '+q(timer)+' '+str(duration-60)+' '+str(duration)+'\nbash mods/pcp-bound/knob.sh 0 512\n')
        for node in NODES:snapshot(node,'activated',512)
        if kind=='native':
            from pcp_native_receipt import validate as validate_native
            def budget(peer,invocation):
                key='native-'+invocation['spelling']+'-budget-before-'+invocation['node']
                checked(peer,key,'test "$(cat /proc/sys/vm/percpu_pagelist_high_fraction)" = 512\n/home/nvidia/.local/bin/uv run --offline --no-project --python /usr/bin/python3 scripts/check_pcp_timer.py '+q(timer)+' 180 600\n')
            def run(invocation):
                node,spelling,run_id=(invocation[k] for k in ('node','spelling','run_id'));key='native-'+spelling
                checked(node,key,'bash mods/pcp-bound/gpu-native.sh '+spelling+' '+run_id+' '+node+'\n')
                return (out/(node+'-'+key+'.log')).read_text()
            def validate(log,invocation):
                node,spelling,run_id=(invocation[k] for k in ('node','spelling','run_id'))
                proof=validate_native(log,spelling,node,run_id);proof['process_exit_verified_by_controller']=True
                (out/(node+'-native-'+spelling+'-proof.json')).write_text(json.dumps(proof,indent=2)+'\n')
                return proof
            proofs=native_suite(plan,budget,run,validate)
            (out/'outcome.json').write_text(json.dumps(proofs,indent=2)+'\n')
            return str(out)
        for node in NODES:
            checked(node,'B','/home/nvidia/.local/bin/uv run --offline --no-project --python /usr/bin/python3 scripts/check_pcp_timer.py '+q(timer)+' 180\nbash mods/pcp-bound/gpu-node.sh 512\n')
            subprocess.run(['/home/nvidia/.local/bin/uv','run','--offline','--no-project','--python','/usr/bin/python3',str(root/'scripts/pcp_micro_receipt.py'),'check',str(out/(node+'-B.log')),'512'],check=True,timeout=10)
        subprocess.run(['/home/nvidia/.local/bin/uv','run','--offline','--no-project','--python','/usr/bin/python3',str(root/'scripts/pcp_micro_receipt.py'),str(out)],check=True,timeout=10)
        return str(out)
    print(with_bookkeeping(lambda:transaction(perform,restore,verify,cancel),bookkeep),flush=True)


if __name__=='__main__':main()
