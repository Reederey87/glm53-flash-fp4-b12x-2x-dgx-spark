"""Persist a small retry budget for a valid but undersized startup cache."""
import fcntl
import json
import math
from pathlib import Path
import re
import time

from flare_watchdog import save

WINDOW = 6 * 60 * 60
MAX_RETRIES = 2
RETRY_EXIT = 75
EXHAUSTED_EXIT = 78


def decide(state, now, invocation, tokens, minimum):
    if (state.get('schema') != 1 or not isinstance(state.get('attempts'), list)
            or not math.isfinite(now) or now < 0
            or re.fullmatch(r'[0-9a-f]{32}', invocation) is None
            or type(tokens) is not int or type(minimum) is not int
            or not 0 < tokens < minimum):
        raise ValueError('invalid startup retry evidence')
    attempts = state['attempts']
    if any(type(t) not in (int, float) or not math.isfinite(t) or t < 0 for t in attempts):
        raise ValueError('invalid startup retry history')
    # Future entries still consume budget after a clock rollback.
    attempts = [t for t in attempts if t > now - WINDOW]
    retry = len(attempts) < MAX_RETRIES
    if retry:
        attempts.append(now)
    return RETRY_EXIT if retry else EXHAUSTED_EXIT, {
        'schema': 1, 'attempts': attempts,
        'last_failure': {'time': now, 'invocation': invocation,
                         'tokens': tokens, 'minimum': minimum,
                         'action': 'retry_after_cleanup' if retry else 'budget_exhausted'},
    }


def record_failure(directory, invocation, tokens, minimum, memory=None):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / 'lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = directory / 'state.json'
        state = json.loads(path.read_text()) if path.exists() else {'schema': 1, 'attempts': []}
        code, updated = decide(state, time.time(), invocation, tokens, minimum)
        if memory:
            # Keep the sizing inputs with the failure that they explain.
            updated['last_failure']['memory_pre_sizing'] = memory
        # Persist before returning the status that authorizes systemd to retry.
        save(path, updated)
        # The owner's EXIT trap accepts exit 75 only when this receipt exists, so
        # an unrelated failure cannot borrow the retry budget.
        if code == RETRY_EXIT:
            (directory / f'retry-{invocation}').write_text('')
    print(json.dumps({'startup_capacity_failure': updated['last_failure'],
                      'retries_in_window': len(updated['attempts'])}), flush=True)
    return code
