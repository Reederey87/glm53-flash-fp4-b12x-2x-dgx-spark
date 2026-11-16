"""Head-only production health checks with persistent, bounded recovery.

The production owner remains active after startup and owns both native ranks.
Stopping that owner manually prevents healing. A failed startup requires operator
attention or the pre-armed production rollback; this watchdog never starts an
inactive/failed owner or resets systemd's failure counters.
"""
import fcntl
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import time
import urllib.request

ROOT = Path('/home/nvidia/b12x-flare')
OWNER = 'b12x-flare-production.service'
WINDOW = 21600
MAX_HEALS = 3


def decision(ledger, now, *, enabled, owner, healthy, maintenance=False):
    """Return an action and next ledger; invalid state fails closed."""
    if ledger.get('schema') != 1 or type(ledger.get('pending')) is not int:
        raise ValueError('invalid watchdog ledger')
    attempts = ledger.get('attempts')
    if (not isinstance(attempts, list) or not math.isfinite(now) or
            any(type(t) not in (int, float) or not math.isfinite(t) or t < 0 for t in attempts) or
            not 0 <= ledger['pending'] <= 2):
        raise ValueError('invalid watchdog history')
    # Future timestamps survive a backward clock adjustment and still consume
    # budget. Never treat a clock rollback as permission for extra restarts.
    next_state = {'schema': 1, 'pending': ledger['pending'],
                  'attempts': [t for t in attempts if t > now - WINDOW]}
    if maintenance or not enabled or owner != 'active':
        next_state['pending'] = 0
        return 'skip', next_state
    if healthy:
        next_state['pending'] = 0
        return 'healthy', next_state
    next_state['pending'] = min(2, next_state['pending'] + 1)
    if next_state['pending'] < 2:
        return 'observe', next_state
    if len(next_state['attempts']) >= MAX_HEALS:
        return 'budget_exhausted', next_state
    next_state['pending'] = 0
    next_state['attempts'].append(now)
    return 'try_restart', next_state


def command(argv):
    return subprocess.run(argv, check=True, capture_output=True, text=True,
                          timeout=15).stdout.strip()


def state(unit, peer=False):
    args = ['systemctl', '--user', 'show', unit, '-p', 'ActiveState', '--value']
    if peer:
        args = ['ssh', '-n', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5',
                'nvidia@192.168.177.11', *args]
    return command(args)


def save(path, value):
    tmp = path.with_suffix('.tmp')
    with tmp.open('w') as output:
        json.dump(value, output)
        output.write('\n')
        output.flush()
        os.fsync(output.fileno())
    tmp.replace(path)


def main():
    if socket.gethostname() != 'spark-a183':
        raise RuntimeError('production watchdog runs only on the head')
    directory = ROOT / 'local/production-watchdog'
    directory.mkdir(exist_ok=True)
    with (directory / 'lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path = directory / 'state.json'
        ledger = json.loads(path.read_text()) if path.exists() else {
            'schema': 1, 'pending': 0, 'attempts': []}
        owner = state(OWNER)
        enabled = subprocess.run(['systemctl', '--user', 'is-enabled', '--quiet', OWNER],
                                 timeout=10).returncode == 0
        maintenance = (ROOT / 'local/production-maintenance').exists()
        healthy = False
        if enabled and owner == 'active' and not maintenance:
            try:
                ranks = [state('b12x-flare@0.service'), state('b12x-flare@1.service', True)]
                with urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=8) as response:
                    healthy = ranks == ['active', 'active'] and response.status == 200
            except (OSError, subprocess.SubprocessError):
                pass
        action, updated = decision(ledger, time.time(), enabled=enabled, owner=owner,
                                   healthy=healthy, maintenance=maintenance)
        # Persist the attempt before dispatch, including failed dispatches. A
        # crash or reboot must not erase an already consumed recovery attempt.
        save(path, updated)
        print(json.dumps({'action': action, 'owner': owner, 'healthy': healthy,
                          'attempts_in_window': len(updated['attempts'])}), flush=True)
        if action == 'try_restart':
            # Unlike restart/start, try-restart will not resurrect an owner
            # stopped by the operator between observation and dispatch.
            command(['systemctl', '--user', 'try-restart', '--no-block', OWNER])


if __name__ == '__main__':
    main()
