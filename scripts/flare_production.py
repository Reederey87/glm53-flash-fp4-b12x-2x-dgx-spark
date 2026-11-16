"""Read-only production pin validation and bounded two-rank readiness."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import socket
import subprocess
import time
import urllib.request

from flare_candidate import RECIPE, load_recipe
from flare_run import serving_command, serving_recipe

ROOT = Path('/home/nvidia/b12x-flare')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fingerprints(recipe, core_bytes):
    return {'recipe_sha256': digest(json.dumps(recipe, sort_keys=True,
                                              separators=(',', ':')).encode()),
            'core_state_sha256': digest(core_bytes),
            'native_arm': recipe.get('native_arm', 'upstream')}


def validate_pin(pin, decision_bytes, actual, rank):
    decision = json.loads(decision_bytes)
    if (pin.get('schema') != 1 or pin.get('decision_sha256') != digest(decision_bytes) or
            pin.get('ranks', {}).get(str(rank)) != actual or
            decision.get('status') != 'qualified' or
            decision.get('native_arm') != actual['native_arm']):
        raise ValueError('production pin or qualification decision does not match runtime')


def rollback_due(pending, now):
    deadline = pending.get('rollback_after')
    if (pending.get('schema') != 1 or type(deadline) not in (int, float) or
            not math.isfinite(deadline) or deadline <= 0):
        raise ValueError('invalid production rollback deadline')
    return now >= deadline


def rank_state(rank):
    command = ['systemctl', '--user', 'show', f'b12x-flare@{rank}.service',
               '-p', 'ActiveState', '--value']
    if rank:
        command = ['ssh', '-n', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5',
                   'nvidia@192.168.177.11', *command]
    return subprocess.check_output(command, text=True, timeout=15).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('fingerprints', 'verify', 'ready', 'rollback-due'))
    parser.add_argument('--rank', type=int, choices=(0, 1), default=0)
    args = parser.parse_args()
    if socket.gethostname() != ('spark-a183', 'spark-7829')[args.rank]:
        raise RuntimeError('unexpected production rank host')
    if args.action == 'rollback-due':
        pending = json.loads((ROOT / 'local/production-pending.json').read_text())
        return 0 if rollback_due(pending, time.time()) else 75
    recipe = serving_recipe(load_recipe(RECIPE))
    core_bytes = (ROOT / 'local/accepted-core.json').read_bytes()
    actual = fingerprints(recipe, core_bytes)
    if args.action == 'fingerprints':
        print(json.dumps(actual))
        return
    validate_pin(json.loads((ROOT / 'local/production-pin.json').read_text()),
                 (ROOT / 'local/production-decision.json').read_bytes(), actual, args.rank)
    if recipe.get('scheduler_trace', 'off') != 'off':
        raise ValueError('production tracing must be off')
    # Checks the selected native executable, patch, locks, publisher and core.
    serving_command(recipe, args.rank, json.loads(core_bytes))
    if args.action == 'verify':
        print(json.dumps({'rank': args.rank, 'production_pin': 'verified', **actual}))
        return
    if args.rank != 0:
        raise ValueError('only head owns cluster readiness')
    deadline = time.monotonic() + 900
    while time.monotonic() < deadline:
        states = [rank_state(rank) for rank in (0, 1)]
        if any(s not in ('active', 'activating') for s in states):
            raise RuntimeError(f'native rank failed during startup: {states}')
        try:
            with urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=3) as response:
                if response.status == 200 and states == ['active', 'active']:
                    print('Both native ranks active; health HTTP 200', flush=True)
                    return
        except OSError:
            pass
        time.sleep(2)
    raise RuntimeError('Flare production readiness deadline exceeded')


if __name__ == '__main__':
    raise SystemExit(main())
