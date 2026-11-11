"""Require a live independent rollback timer with a measured remaining budget."""
import re
import subprocess
import sys
import time

if __name__=='__main__':
    if len(sys.argv)!=3 or not re.fullmatch(r'b12x-pcp512-rollback-\d{8}t\d{6}z',sys.argv[1]):raise ValueError('unexpected timer')
    budget=int(sys.argv[2])
    if budget not in (180,240):raise ValueError('unregistered time budget')
    unit=sys.argv[1]+'.timer'
    subprocess.run(['systemctl','--user','is-active','--quiet',unit],check=True,timeout=5)
    entered=int(subprocess.check_output(['systemctl','--user','show',unit,'-p','ActiveEnterTimestampMonotonic','--value'],text=True,timeout=5).strip())
    remaining=300-(time.monotonic_ns()/1000-entered)/1e6
    if entered<=0 or not budget<=remaining<=301:raise ValueError('rollback timer budget insufficient')
    print('B12X_PCP_TIMER_REMAINING_SECONDS',remaining,flush=True)
