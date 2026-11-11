"""Real Linux user-systemd lifecycle, with ALL cluster/benchmark calls mocked.

Fixtures shorten supervisor polling to 0.1s; production remains 2s. Only unique
b12x-review-recipe-* units are managed for real. No model/API is touched.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import uuid

SCRIPTS = Path(__file__).resolve().parent
TASK = 'draft-b12x'
IMAGE = 'sha256:3b5da79c42ed4204440cfb07c6de1eba46441d5cba6b57d5428d44e60c10d0ed'


def real(*args, **kw):
    return subprocess.run(args, check=True, capture_output=True, text=True, **kw)


def wait_for(test, seconds=30):
    end = time.monotonic()+seconds
    while time.monotonic()<end:
        if test(): return
        time.sleep(.1)
    raise TimeoutError('test phase timed out')


def scenario(mode, failure, recovery_failure='none', guarded=False, stop_only=False, warmup=False, ownership=False, host_trim=False, compiler=False, release=False, pinned=False):
    with tempfile.TemporaryDirectory(prefix='b12x-review-recipe-') as tmp:
        root=Path(tmp); out=root/f'local/ab-{TASK}'
        out.mkdir(parents=True)
        for path in ('scripts', 'bin', 'recipes/windows', 'recipes/candidates'):
            (root/path).mkdir(parents=True, exist_ok=True)
        for name in ('recipe_window.sh', 'recipe_recover.sh'):
            source=(SCRIPTS/name).read_text().replace('/home/nvidia/.local/bin/uv',str(root/'bin/uv'))
            source=source.replace('sleep 2 & wait $!', 'sleep 0.1 & wait $!')
            (root/'scripts'/name).write_text(source)
        (root/'scripts/window_profile.py').write_text('# mock docker exec stdin\n')
        shutil.copy(SCRIPTS.parent/f'recipes/windows/{TASK}.conf',root/f'recipes/windows/{TASK}.conf')
        if guarded:
            with (root/f'recipes/windows/{TASK}.conf').open('a') as stream:
                stream.write('\nRECOVERY_GUARD=1\nRECOVERY_RECIPE=recipes/glm-5.3-flash-fp4-local.yaml\nRECOVERY_LOADER_SHA256=aa398e74ee835537403e60186f2e9a81e8741a4b35fec68b47df6537716a45b7\n')
        if mode=='observation' or stop_only:
            (root/'recipes/observations').mkdir()
            (root/'recipes/observations/startup-memory.yaml').write_text('fixture observation\n')
            with (root/f'recipes/windows/{TASK}.conf').open('a') as stream:
                stream.write('\nWINDOW_KIND=observation\nCONTROL_RECIPE=recipes/observations/startup-memory.yaml\nRECOVERY_RECIPE=recipes/glm-5.3-flash-fp4-local.yaml\nTRACE_LOADER_SHA256=fixture\n')
            (root/'mods/startup-memory').mkdir(parents=True)
            (root/'mods/startup-memory/trace.py').write_text('# fixture\n')
        if stop_only:
            with (root/f'recipes/windows/{TASK}.conf').open('a') as stream:
                stream.write('\nWINDOW_KIND=stabilization\nRECOVERY_MODE=stop-only\n')
            (root/'mods/startup-bound').mkdir(parents=True)
            (root/'mods/startup-bound/bound.py').write_text('# fixture\n')
        if warmup:
            with (root/f'recipes/windows/{TASK}.conf').open('a') as stream:
                stream.write('\nWARMUP_CACHE_RETURN=1\nWARMUP_WORKER_SHA256=fixture\nWARMUP_CACHE_MIN_HEAD=67108864\n')
            (root/'mods/warmup-cache-return').mkdir(parents=True)
            (root/'mods/warmup-cache-return/release.py').write_text('# fixture\n')
        if ownership:
            with (root/f'recipes/windows/{TASK}.conf').open('a') as stream:
                stream.write('\nHOST_OWNERSHIP=1\nOWNERSHIP_WORKER_SHA256=fixture\nOWNERSHIP_HELPER=mods/host-ownership-entry/observe.py\nOWNERSHIP_BOUNDARY=pre-warmup\n')
            (root/'mods/host-ownership-entry').mkdir(parents=True)
            (root/'mods/host-ownership-entry/observe.py').write_text('# fixture\n')
        if host_trim:
            (out/'host-trim-active').touch()
            with (root/f'recipes/windows/{TASK}.conf').open('a') as stream:
                stream.write('\nHOST_TRIM=1\nTRIM_WORKER_SHA256=fixture\nTRIM_MINIMUM_RECLAIM=1073741824\n')
            (root/'mods/explicit-kv-host-trim').mkdir(parents=True)
            (root/'mods/explicit-kv-host-trim/trim.py').write_text('# fixture\n')
        if compiler:
            with (root/f'recipes/windows/{TASK}.conf').open('a') as stream:
                stream.write('\nOWNERSHIP_VALIDATOR=scripts/compiler_ownership_receipt.py\nOWNERSHIP_HELPER=mods/compiler-ownership/observe.py\nOWNERSHIP_METADATA=mods/compiler-ownership/metadata.py\nOWNERSHIP_BOUNDARY=post-explicit-profile\n')
            (root/'mods/compiler-ownership').mkdir(parents=True)
            (root/'mods/compiler-ownership/observe.py').write_text('# fixture\n')
            (root/'mods/compiler-ownership/metadata.py').write_text('# fixture metadata\n')
        if release:
            (out/'compiler-release-active').touch()
            with (root/f'recipes/windows/{TASK}.conf').open('a') as stream:
                stream.write('\nCOMPILER_RELEASE=1\nRELEASE_WORKER_SHA256=fixture\nRELEASE_MINIMUM_RECLAIM=1073741824\n')
            (root/'mods/compiler-cache-release').mkdir(parents=True)
            (root/'mods/compiler-cache-release/release.py').write_text('# fixture\n')
        if pinned:
            (out/'pinned-return-active').touch()
            with (root/f'recipes/windows/{TASK}.conf').open('a') as stream:
                stream.write('\nPINNED_RETURN=1\nPINNED_WORKER_SHA256=fixture\n')
            (root/'mods/startup-pinned').mkdir(parents=True)
            (root/'mods/startup-pinned/release.py').write_text('# fixture\n')
        recipe=root/'recipes/glm-5.3-flash-fp4-local.yaml'; recipe.write_text('fixture control\n')
        (root/f'recipes/candidates/{TASK}.yaml').write_text('fixture candidate\n')
        (root/'.env').write_text('B12X_ALLOCATOR_CONF=\n')
        (out/'frozen.sha256').write_text(real('sha256sum',str(recipe)).stdout)
        mock=r'''#!/bin/bash
set -eu
cd "$B12X_TEST_ROOT"
OUT="$B12X_TEST_ROOT/local/ab-draft-b12x"
echo "$(basename "$0") $*" >> "$OUT/events"
candidate() { grep '^RECIPE=' .env | tail -n1 | grep -q '/recipes/candidates/'; }
case "$(basename "$0")" in
 systemctl)
  case "$*" in
   *' -p MainPID --value'*) echo 0;;
   *' -p ActiveState --value'*) echo inactive;;
   *'show b12x-draft-b12x-recovery-memory.service -p InvocationID'*) echo fake-recovery;;
   *'show b12x-draft-b12x-recovery-memory.service -p ActiveState'*)
    echo 'ActiveState=inactive'; echo 'SubState=dead'; echo 'ExecMainStatus=0'
    if [ "$B12X_TEST_RECOVERY" = recovery-terminal ]; then echo 'Result=exit-code'; else echo 'Result=success'; fi;;
   *'is-active --quiet b12x-draft-b12x-recovery-memory.service'*)
    test -f "$OUT/active-recovery"
    stamp=$(date +%s)
    if [ -e "$OUT/inject-heartbeat" ]; then
      case "$B12X_TEST_RECOVERY" in recovery-stale) stamp=$((stamp-30));; recovery-future) stamp=$((stamp+30));; esac
    fi
    echo "fake-recovery $stamp" > "$OUT/recovery-memory.csv.ready";;
   *'show b12x-draft-b12x-memory-a.service -p InvocationID'*) echo fake-a;;
   *'show b12x-draft-b12x-memory-b.service -p InvocationID'*) echo fake-b;;
   *'show vllm-b12x-watchdog'*|*'show vllm-b12x-tailscale'*) echo inactive;;
   *'is-active --quiet b12x-draft-b12x-memory-a.service'*) test -f "$OUT/active-a";;
   *'is-active --quiet b12x-draft-b12x-memory-b.service'*) test -f "$OUT/active-b";;
   *'is-active'*) echo active;;
   *'stop vllm-b12x-watchdog.timer '*)
    case "$*" in *tailscale*) rm -f "$OUT/proxy-active";; esac
    if [ "$B12X_TEST_MODE" = isolation ]; then
      touch "$OUT/phase"; if [ "$B12X_TEST_FAILURE" = stop-failure ]; then exit 1; fi
      exec sleep 300
    fi;;
   *'start vllm-b12x.service'*)
    if [ "$B12X_TEST_MODE" = stabilization-startup ]; then touch "$OUT/phase"; exec sleep 300; fi
    if candidate && [ "$B12X_TEST_MODE" = startup ]; then touch "$OUT/phase"; exec sleep 300; fi
    if [ -e "$OUT/active-recovery" ]; then
      case "$B12X_TEST_RECOVERY" in
       recovery-floor) touch "$OUT/recovery-memory.csv.abort"; exit 1;;
       recovery-observer) rm -f "$OUT/active-recovery";;
       recovery-stale|recovery-future) touch "$OUT/inject-heartbeat";;
       recovery-startup-loss) touch "$OUT/rollback-phase"; exec sleep 300;;
      esac
    fi
    sleep .1;;
   *'start vllm-b12x-tailscale.service'*)
    touch "$OUT/proxy-active"; if [ "$B12X_TEST_RECOVERY" = proxy-failure ]; then exit 1; fi;;
   *'stop vllm-b12x-tailscale.service'*) rm -f "$OUT/proxy-active";;
   *'stop b12x-draft-b12x-recovery-memory.service'*)
    if [ "$B12X_TEST_RECOVERY" = recovery-stop-race ]; then touch "$OUT/recovery-memory.csv.abort"; fi
    rm -f "$OUT/active-recovery";;
   *'stop '*|*'start '*|*'reset-failed '*) :;;
   *) exit 99;;
  esac;;
 systemd-run)
  case "$*" in *memory-a*) arm=a;; *memory-b*) arm=b;; *recovery-memory*)
   touch "$OUT/active-recovery"; echo "fake-recovery $(date +%s)" > "$OUT/recovery-memory.csv.ready"; exit 0;;
   *) exit 99;; esac
  touch "$OUT/active-$arm"; echo "fake-$arm $(date +%s)" > "$OUT/memory-$arm.csv.ready";;
 docker)
  case "$*" in
   'ps -a '*) if [ "$B12X_TEST_FAILURE" = containers-present ]; then echo leftover-container; fi;;
   *'.Image'*) echo "$B12X_TEST_IMAGE";;
   'exec vllm_node sha256sum '*) echo 'aa398e74ee835537403e60186f2e9a81e8741a4b35fec68b47df6537716a45b7 utils.py';;
   'exec -i '*)
    script=$(cat)
    [ "$script" = '# mock docker exec stdin' ] || exit 97
    echo '{"mock":true}' ;;
   'logs '*) echo 'GPU KV cache size: 2,350,210 tokens'
    if [ -e "$OUT/compiler-release-active" ]; then printf 'B12X_COMPILER_RELEASE {}\nB12X_COMPILER_RELEASE {}\n'; fi
    if [ -e "$OUT/pinned-return-active" ]; then printf 'B12X_PINNED_RETURN {}\nB12X_PINNED_RETURN {}\n'; fi
    if [ -e "$OUT/host-trim-active" ]; then printf 'B12X_HOST_TRIM {}\nB12X_HOST_TRIM {}\n'; fi
    if [ "$B12X_TEST_MODE" = ownership ] && [ "$B12X_TEST_FAILURE" != ownership-missing-both ]; then
      if [ "$B12X_TEST_FAILURE" != ownership-missing-worker ] || [ "${B12X_MOCK_REMOTE:-0}" != 1 ]; then echo 'B12X_HOST_OWNERSHIP {}'; fi
    fi
    case "$*" in *--follow*) exec sleep 300;; esac;;
   *) exit 99;;
  esac;;
 ssh)
  while true; do case "${1:-}" in -o) shift 2;; -n) shift;; *) break;; esac; done
  shift; export B12X_MOCK_REMOTE=1; exec /bin/bash -c "$*";;
 curl) :;;
 uv)
  case "$*" in
   *'window_profile.py --check'*) echo 'profile verified';;
   *startup_trace_receipt.py*) test ! -e "$OUT/trace-floor"; echo 'mock complete trace';;
   *startup_bound_receipt.py*) echo 'mock completed bound scopes';;
   *warmup_cache_receipt.py*)
    [ "$B12X_TEST_FAILURE" != warmup-evidence ]
    echo 'mock cache return proof';;
   *host_ownership_receipt.py*)
    case "$*" in *'--boundary pre-warmup'*) :;; *) exit 96;; esac
    [ "$B12X_TEST_FAILURE" != ownership-evidence ]; echo 'mock ownership proof';;
   *host_trim_receipt.py*) [ "$B12X_TEST_FAILURE" != trim-evidence ]; echo 'mock trim proof';;
   *compiler_ownership_receipt.py*)
    case "$*" in *'--boundary post-explicit-profile --metadata '*) :;; *) exit 95;; esac
    [ "$B12X_TEST_FAILURE" != ownership-evidence ]; echo 'mock compiler proof';;
   *compiler_release_receipt.py*) [ "$B12X_TEST_FAILURE" != release-evidence ]; echo 'mock compiler release proof';;
   *pinned_cache_receipt.py*) [ "$B12X_TEST_FAILURE" != pinned-evidence ]; echo 'mock pinned return proof';;
   *'run --offline python -c '*) echo '2,350,210';;
   *smoke.py*)
    if [ -e "$OUT/active-recovery" ] && [ "$B12X_TEST_RECOVERY" = recovery-smoke-loss ]; then
      touch "$OUT/rollback-phase"; exec sleep 300
    fi
    if ! candidate && [ -e "$OUT/recovery-required" ] && [ -e "$OUT/b-seen" ] && [ "$B12X_TEST_RECOVERY" = hold-rollback ] && [ ! -e "$OUT/held-once" ]; then
      touch "$OUT/held-once" "$OUT/rollback-phase"; exec sleep 300
    fi
    echo '5/5 checks passed hard';;
   *compare_matrix.py*) echo 'mock receipt validator';;
   *parity.py*) :;;
   *speed_matrix.py*)
    dest=; prev=
    for arg in "$@"; do if [ "$prev" = --out ]; then dest="$arg"; fi; prev="$arg"; done
    printf '{}\n' > "$dest"
    case "$*" in *-probe*) exit 0;; esac
    if [ "$B12X_TEST_MODE" = stabilization-measurement ]; then touch "$OUT/phase"; exec sleep 300; fi
    if ! candidate && [ "$B12X_TEST_FAILURE" = control-failure ]; then touch "$OUT/phase"; exit 1; fi
    if candidate; then touch "$OUT/b-seen" "$OUT/phase"; exec sleep 300; fi;;
   *) exit 99;;
  esac;;
 *) exit 99;;
esac
'''
        for name in ('systemctl','systemd-run','docker','ssh','curl','uv'):
            p=root/'bin'/name; p.write_text(mock); p.chmod(0o755)
        unit='b12x-review-recipe-'+uuid.uuid4().hex[:12]
        try:
            real('systemd-run','--user','--unit='+unit,'--property=KillMode=mixed','--property=TimeoutStopSec=30',
                 '--property=ExecStopPost=/bin/bash '+str(root/'scripts/recipe_recover.sh')+' '+TASK,
                 '--setenv=PATH='+str(root/'bin')+':/usr/bin:/bin','--setenv=B12X_TEST_ROOT='+str(root),
                 '--setenv=B12X_TEST_MODE='+mode,'--setenv=B12X_TEST_FAILURE='+failure,
                 '--setenv=B12X_TEST_RECOVERY='+recovery_failure,'--setenv=B12X_TEST_IMAGE='+IMAGE,
                 '/bin/bash',str(root/'scripts/recipe_window.sh'),TASK)
            if mode not in ('observation','stabilization','ownership'):
                wait_for(lambda:(out/'phase').exists())
                if failure=='guard-failure': (out/('active-a' if stop_only else 'active-b')).unlink()
                elif failure=='trace-floor': (out/'trace-floor').touch()
                elif failure not in ('stop-failure','control-failure'):
                    real('/usr/bin/systemctl','--user','kill','--kill-whom=main','--signal='+failure,unit)
            if recovery_failure=='hold-rollback':
                wait_for(lambda:(out/'rollback-phase').exists())
                real('/usr/bin/systemctl','--user','kill','--kill-whom=main','--signal=SIGKILL',unit)
            if recovery_failure in ('recovery-startup-loss','recovery-smoke-loss'):
                wait_for(lambda:(out/'rollback-phase').exists())
                (out/'active-recovery').unlink()
            terminal=lambda:real('/usr/bin/systemctl','--user','show',unit,'-p','ActiveState','--value').stdout.strip() in ('failed','inactive')
            if stop_only:
                if failure=='containers-present':
                    wait_for(terminal)
                    assert (out/'recovery-required').exists()
                    assert (out/'recovery-failed.txt').exists()
                    assert not (out/'recovery-stopped.txt').exists()
                else:
                    wait_for(lambda:(out/'recovery-stopped.txt').exists())
                    wait_for(terminal)
                    assert not (out/'recovery-required').exists()
                    ledger=(root/'.env').read_text()
                    assert [x for x in ledger.splitlines() if x.startswith('RECIPE=')][-1]=='RECIPE='+str(recipe)
                assert not (out/'proxy-active').exists()
                assert not (out/'recovery-success.txt').exists()
                assert (out/'events').read_text().count('systemctl --user start vllm-b12x.service')==1
                if warmup:
                    events=(out/'events').read_text()
                    assert 'warmup_cache_receipt.py' in events
                    if failure=='warmup-evidence':assert 'scripts/smoke.py' not in events
                if ownership:
                    events=(out/'events').read_text()
                    if failure not in ('ownership-missing-both','ownership-missing-worker'):
                        assert ('compiler_ownership_receipt.py' if compiler else 'host_ownership_receipt.py') in events
                    else:
                        assert (out/'diagnostic-failed.txt').exists()
                    assert 'scripts/smoke.py' not in events
                    assert not (out/'matrix-a.json').exists()
                    assert (out/'diagnostic-captured.txt').exists() == (failure=='none')
                if host_trim:
                    events=(out/'events').read_text()
                    assert 'host_trim_receipt.py' in events
                    if failure=='trim-evidence': assert 'scripts/smoke.py' not in events
                if release:
                    events=(out/'events').read_text()
                    assert 'compiler_release_receipt.py' in events
                    if failure=='release-evidence': assert 'scripts/smoke.py' not in events
                return {'phase':mode,'failure':failure,'verified_stop_only':failure!='containers-present','cleanup_failed_closed':failure=='containers-present'}
            if recovery_failure=='proxy-failure' or recovery_failure.startswith('recovery-'):
                wait_for(terminal)
                assert not (out/'proxy-active').exists()
                assert (out/'recovery-required').exists()
                assert (out/'recovery-failed.txt').exists()
                if guarded:
                    events=(out/'events').read_text()
                    assert events.count('systemctl --user start vllm-b12x.service')==3
                    assert 'stop vllm-b12x-watchdog.timer vllm-b12x-watchdog.service' in events
                    assert not (out/'active-recovery').exists()
                return {'phase':mode,'failure':recovery_failure,'guarded':guarded,'failed_closed':True}
            wait_for(lambda:(out/'recovery-success.txt').exists())
            wait_for(terminal)
            ledger=(root/'.env').read_text()
            assert ledger.splitlines()[-1]=='B12X_ALLOCATOR_CONF='
            assert [x for x in ledger.splitlines() if x.startswith('RECIPE=')][-1]=='RECIPE='+str(recipe)
            assert not (out/'recovery-required').exists()
            assert (out/'proxy-active').exists()
            if failure=='control-failure':
                assert '/recipes/candidates/' not in ledger
            if mode=='observation':
                assert (out/'observation-validation.md').exists()
                assert not (out/'comparison.md').exists()
                assert len([x for x in ledger.splitlines() if x.startswith('RECIPE=')])==2
                assert int((out/'primary-status.txt').read_text())==0
            elif failure!='SIGKILL' and recovery_failure!='hold-rollback':
                assert int((out/'primary-status.txt').read_text())!=0
                assert int((out/'recovery-status.txt').read_text())==0
            if guarded: assert not (out/'active-recovery').exists()
            return {'phase':mode,'failure':failure,'recovery_failure':recovery_failure,'guarded':guarded,'restored':True}
        finally:
            subprocess.run(['/usr/bin/systemctl','--user','stop',unit],capture_output=True,timeout=40)
            subprocess.run(['/usr/bin/systemctl','--user','reset-failed',unit],capture_output=True)


if __name__=='__main__':
    rows=[scenario(mode,failure) for mode in ('startup','measurement') for failure in ('SIGTERM','SIGKILL','guard-failure')]
    rows += [scenario('measurement','SIGTERM',failure) for failure in ('proxy-failure','hold-rollback')]
    rows += [scenario('isolation',failure) for failure in ('SIGTERM','SIGKILL','stop-failure')]
    rows += [scenario('measurement','control-failure')]
    rows += [scenario('measurement','SIGTERM',failure,True) for failure in ('none','recovery-floor','recovery-observer','proxy-failure','recovery-stale','recovery-future','recovery-startup-loss','recovery-smoke-loss','recovery-stop-race','recovery-terminal','hold-rollback')]
    rows += [scenario('observation','none',guarded=True)]
    rows += [scenario(mode,failure,guarded=True,stop_only=True) for mode,failure in
        [('stabilization','none'),('stabilization','containers-present'),
         ('stabilization-startup','SIGTERM'),('stabilization-startup','SIGKILL'),
         ('stabilization-startup','guard-failure'),('stabilization-startup','trace-floor'),
         ('stabilization-measurement','SIGTERM'),('stabilization-measurement','SIGKILL')]]
    rows += [scenario('stabilization',failure,guarded=True,stop_only=True,warmup=True) for failure in ('none','warmup-evidence')]
    rows += [scenario('ownership',failure,guarded=True,stop_only=True,ownership=True) for failure in ('none','ownership-evidence','ownership-missing-both','ownership-missing-worker')]
    rows += [scenario('stabilization',failure,guarded=True,stop_only=True,host_trim=True) for failure in ('none','trim-evidence')]
    rows += [scenario('ownership',failure,guarded=True,stop_only=True,ownership=True,compiler=True) for failure in ('none','ownership-evidence','ownership-missing-both','ownership-missing-worker')]
    rows += [scenario('stabilization',failure,guarded=True,stop_only=True,release=True) for failure in ('none','release-evidence')]
    rows += [scenario('stabilization',failure,guarded=True,stop_only=True,pinned=True) for failure in ('none','pinned-evidence')]
    print(json.dumps({'poll_override_seconds':.1,'scenarios':rows},indent=2))
