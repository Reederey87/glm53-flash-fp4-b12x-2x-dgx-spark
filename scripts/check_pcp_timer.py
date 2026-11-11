"""Require a live independent rollback timer with a measured remaining budget."""
import re
import subprocess
import sys
import time


def budget_remaining(entered,deadline,now,duration,budget):
    if (duration,budget) not in ((300,180),(300,240),(600,180),(600,540)):
        raise ValueError('unregistered time budget')
    if entered<=0 or entered>now or abs(deadline-entered-duration*1_000_000)>1_000_000:
        raise ValueError('actual rollback deadline differs from registered duration')
    remaining=(deadline-now)/1e6
    if not budget<=remaining<=duration+1:raise ValueError('rollback timer budget insufficient')
    return remaining


if __name__=='__main__':
    if len(sys.argv) not in (3,4) or not re.fullmatch(r'b12x-pcp512-rollback-\d{8}t\d{6}z',sys.argv[1]):raise ValueError('unexpected timer')
    budget=int(sys.argv[2]);duration=300 if len(sys.argv)==3 else int(sys.argv[3])
    unit=sys.argv[1]+'.timer'
    subprocess.run(['systemctl','--user','is-active','--quiet',unit],check=True,timeout=5)
    entered=int(subprocess.check_output(['systemctl','--user','show',unit,'-p','ActiveEnterTimestampMonotonic','--value'],text=True,timeout=5).strip())
    path='/org/freedesktop/systemd1/unit/'+unit.replace('_','_5f').replace('-','_2d').replace('.','_2e')
    raw=subprocess.check_output(['busctl','--user','get-property','org.freedesktop.systemd1',path,
        'org.freedesktop.systemd1.Timer','NextElapseUSecMonotonic'],text=True,timeout=5).split()
    if len(raw)!=2 or raw[0]!='t' or not raw[1].isdecimal():raise ValueError('invalid actual timer deadline')
    remaining=budget_remaining(entered,int(raw[1]),time.monotonic_ns()//1000,duration,budget)
    print('B12X_PCP_TIMER_REMAINING_SECONDS',remaining,flush=True)
