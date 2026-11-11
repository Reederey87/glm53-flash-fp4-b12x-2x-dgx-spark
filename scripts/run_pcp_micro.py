"""Head-side temporary both-node transaction; timers independently roll back."""
import argparse
from datetime import datetime,timezone
from pathlib import Path
import os
import shlex
import signal
import subprocess

NODES=('head','worker')


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
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true',required=True);parser.parse_args()
    def interrupted(signum,frame):raise KeyboardInterrupt('signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGHUP,interrupted)
    root=Path(__file__).resolve().parents[1]
    if not str(root).startswith('/home/nvidia/b12x-staging/pcp-bound-'):raise ValueError('inactive staging tree required')
    if root.stat().st_uid!=os.getuid() or root.stat().st_mode&0o077:raise ValueError('private owned staging tree required')
    label=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out=Path('/home/nvidia/b12x/local')/('pcp-bound-'+label);out.mkdir(exist_ok=False)
    timer='b12x-pcp512-rollback-'+label.lower();q=shlex.quote
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
        execute(node,'restore','set -eu\nbash '+q(str(root/'mods/pcp-bound/rollback.sh'))+'\n')
    def verify(node):
        snapshot(node,'restored',0)
        execute(node,'no-containers','test -z "$(docker ps -q)"\n')
        execute(node,'ledger-restored','printf %s '+q('# PCP micro '+label+' policy restored0; see local/pcp-bound-'+label+'/ receipts; no adoption\n')+' >> /home/nvidia/b12x/.env\n')
    def cancel(node):execute(node,'timer-cancel','systemctl --user stop '+q(timer+'.timer')+' '+q(timer+'.service')+'\n')
    def perform():
        for node in NODES:
            checked(node,'preflight','''test -z "$(docker ps -q)"
test "$(systemctl --user show vllm-b12x.service -p MainPID --value)" = 0
! systemctl --user is-active --quiet vllm-b12x-watchdog.timer
! systemctl --user is-active --quiet vllm-b12x-tailscale.service
''')
            snapshot(node,'before',0)
            backup='/home/nvidia/b12x/.env.bak-pcp-bound-'+label
            checked(node,'ledger','test ! -e '+q(backup)+'\ncp -n /home/nvidia/b12x/.env '+q(backup)+'\nsha256sum '+q(backup)+'\nprintf %s '+q('# PCP micro '+label+' policy0->512; unchanged model off,17GKV,2GiBfloor,minfree; rollback0; gate docs/gates/pcp-bound-micro.md\n')+' >> /home/nvidia/b12x/.env\n')
        for node in NODES:checked(node,'A','bash mods/pcp-bound/gpu-node.sh 0\n')
        for node in NODES:
            checked(node,'timer-arm','test ! -e .pcp-lease\nprintf "armed\\n" > .pcp-lease\ntouch .pcp-lock\nchmod 666 .pcp-lease .pcp-lock\nsystemd-run --user --unit='+q(timer)+' --on-active=300s --timer-property=AccuracySec=1s --property=Restart=on-failure --property=RestartSec=5s --property=StartLimitIntervalSec=0 /bin/bash '+q(str(root/'mods/pcp-bound/rollback.sh'))+'\nsystemctl --user is-active --quiet '+q(timer+'.timer')+'\n')
        for node in NODES:checked(node,'apply','/home/nvidia/.local/bin/uv run --offline --no-project --python /usr/bin/python3 scripts/check_pcp_timer.py '+q(timer)+' 240\nbash mods/pcp-bound/knob.sh 0 512\n')
        for node in NODES:snapshot(node,'activated',512)
        for node in NODES:checked(node,'B','/home/nvidia/.local/bin/uv run --offline --no-project --python /usr/bin/python3 scripts/check_pcp_timer.py '+q(timer)+' 180\nbash mods/pcp-bound/gpu-node.sh 512\n')
        subprocess.run(['/home/nvidia/.local/bin/uv','run','--offline','--no-project','--python','/usr/bin/python3',str(root/'scripts/pcp_micro_receipt.py'),str(out)],check=True,timeout=10)
        return str(out)
    print(transaction(perform,restore,verify,cancel),flush=True)


if __name__=='__main__':main()
