"""Read-only production pin validation and bounded two-rank readiness."""
import argparse
import hashlib
import json
import math
import re
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
            decision.get('native_arm') != actual['native_arm']):
        raise ValueError('production pin or qualification decision does not match runtime')
    capacity_floor(decision)
    return decision


def capacity_floor(decision):
    """Keep full qualification distinct from an explicitly approved release."""
    if decision.get('status') == 'qualified':
        return 2350210
    if (decision.get('status') == 'approved-provisional'
            and decision.get('approved_by_user') is True
            and decision.get('minimum_kv_tokens') == 2300000
            and isinstance(decision.get('open_gates'), list)
            and decision['open_gates']
            and all(isinstance(g, str) and g.strip() for g in decision['open_gates'])):
        return 2300000
    raise ValueError('production requires qualification or explicit provisional approval with open gates')


def rollback_due(pending, now):
    deadline = pending.get('rollback_after')
    if (pending.get('schema') != 1 or type(deadline) not in (int, float) or
            not math.isfinite(deadline) or deadline <= 0):
        raise ValueError('invalid production rollback deadline')
    return now >= deadline


def validate_capacity(scrape, minimum_tokens=2350210):
    """Enforce the registered pool floor on every production start/recovery."""
    names = ('flare_total_kv_pages', 'flare_kv_page_tokens', 'flare_total_kv_tokens')
    values = {}
    for name in names:
        rows = [row.split() for row in scrape.splitlines()
                if row.split() and row.split()[0] == name]
        if (len(rows) != 1 or len(rows[0]) != 2 or
                re.fullmatch(r'[0-9]+', rows[0][1]) is None):
            raise ValueError(f'missing or invalid production capacity metric: {name}')
        values[name] = int(rows[0][1])
    pages, page_tokens, tokens = (values[name] for name in names)
    if pages <= 0 or page_tokens <= 0 or pages * page_tokens != tokens:
        raise ValueError('inconsistent production cache geometry')
    if type(minimum_tokens) is not int or minimum_tokens not in (2300000, 2350210):
        raise ValueError('invalid production capacity floor')
    if tokens < minimum_tokens:
        raise ValueError(f'production cache capacity {tokens} is below the {minimum_tokens}-token gate')
    return values


def rank_state(rank):
    command = ['systemctl', '--user', 'show', f'b12x-flare@{rank}.service',
               '-p', 'ActiveState', '--value']
    if rank:
        command = ['ssh', '-n', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5',
                   'nvidia@192.168.177.11', *command]
    return subprocess.check_output(command, text=True, timeout=15).strip()


def startup_progress(states, started):
    """Allow worker dispatch latency, but never a rank disappearing after start."""
    if len(states) != 2 or len(started) != 2:
        raise ValueError('expected two production ranks')
    for rank, state in enumerate(states):
        if state in ('active', 'activating'):
            started[rank] = True
        elif not (rank == 1 and state == 'inactive' and not started[rank]):
            raise RuntimeError(f'native rank failed during startup: {states}')
    return started


def start_ranks():
    # Dispatch a fresh worker invocation before readiness can inspect a retained
    # failed state. Type=exec waits only for supervisor exec, not rendezvous.
    subprocess.run(['ssh', '-n', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5',
                    'nvidia@192.168.177.11', 'systemctl', '--user', 'start',
                    'b12x-flare@1.service'], check=True, timeout=20)
    subprocess.run(['systemctl', '--user', 'start', 'b12x-flare@0.service'],
                   check=True, timeout=20)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('fingerprints', 'verify', 'ready', 'rollback-due', 'start-ranks'))
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
    decision = validate_pin(json.loads((ROOT / 'local/production-pin.json').read_text()),
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
    if args.action == 'start-ranks':
        start_ranks()
        return
    deadline = time.monotonic() + 900
    started = [False, False]
    while time.monotonic() < deadline:
        states = [rank_state(rank) for rank in (0, 1)]
        started = startup_progress(states, started)
        try:
            with urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=3) as response:
                if response.status == 200 and states == ['active', 'active']:
                    with urllib.request.urlopen('http://127.0.0.1:8001/metrics', timeout=5) as metrics:
                        capacity = validate_capacity(metrics.read().decode(), capacity_floor(decision))
                    print(json.dumps({'ranks': states, 'health': 200, 'capacity': capacity,
                                      'release_status': decision['status']}), flush=True)
                    return
        except OSError:
            pass
        time.sleep(2)
    raise RuntimeError('Flare production readiness deadline exceeded')


if __name__ == '__main__':
    raise SystemExit(main())
