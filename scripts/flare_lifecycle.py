"""Exercise candidate-only shutdown or peer loss during observed active decode.

Run on the head after measured clients and the enforcing memory monitor stop.
This deliberately stops Flare. The separate restoration timer must remain armed.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import socket
import subprocess
import threading
import time
import urllib.request

from flare_smoke import runtime_metrics

BASE = 'http://127.0.0.1:8001'
SSH = ['ssh', '-n', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5',
       'nvidia@192.168.177.11']
UNITS = ('b12x-flare@0.service', 'b12x-flare@1.service')
STATE_FIELDS = ('ActiveState', 'SubState', 'MainPID', 'Result', 'ExecMainCode', 'ExecMainStatus')
GAUGES = ('flare_active_requests', 'flare_http_inflight_requests',
          'flare_retiring_request_slots')


def command(rank, args):
    return subprocess.run((SSH if rank else []) + args, check=True,
                          text=True, capture_output=True, timeout=20).stdout


def state(rank):
    text = command(rank, ['systemctl', '--user', 'show', UNITS[rank],
                         '--all', '--property=' + ','.join(STATE_FIELDS)])
    result = dict(line.split('=', 1) for line in text.splitlines() if '=' in line)
    if result.keys() != set(STATE_FIELDS) or any(not value for value in result.values()):
        raise ValueError('missing unit state evidence')
    return result


def terminal(states):
    return all(s['ActiveState'] in ('inactive', 'failed') and s['MainPID'] == '0'
               for s in states)


def invocation_id(rank):
    value = command(rank, ['systemctl', '--user', 'show', UNITS[rank],
                           '--property=InvocationID', '--value']).strip()
    if re.fullmatch(r'[0-9a-f]{32}', value) is None:
        raise ValueError('missing service invocation identity')
    return value


def native_exit(rank, invocation):
    path = f'/home/nvidia/b12x-flare/local/native-exit-serve-rank{rank}-{invocation}.json'
    result = json.loads(command(rank, ['cat', path]))
    expected = {'schema': 1, 'event': 'native_exit', 'action': 'serve',
                'rank': rank, 'invocation_id': invocation}
    if (any(result.get(k) != v for k, v in expected.items()) or
            type(result.get('native_returncode')) is not int or
            type(result.get('native_pid')) is not int or result['native_pid'] <= 0 or
            type(result.get('forced_kill')) is not bool or
            type(result.get('shutdown_requested')) is not bool):
        raise ValueError('missing or mismatched native exit evidence')
    return result


def check_result(action, states, native):
    if not terminal(states):
        raise ValueError('candidate ranks did not terminate')
    if action == 'graceful':
        if any(s['Result'] != 'success' or s['ExecMainStatus'] != '0' for s in states):
            raise ValueError('intentional shutdown was not clean on both ranks')
        # Rank zero initiates coordinated native drain. The worker may exit0
        # before its supervisor receives a local SIGTERM; that is normal.
        if (len(native) != 2 or not native[0]['shutdown_requested'] or
                any(n['native_returncode'] != 0 or n['forced_kill'] for n in native)):
            raise ValueError('actual native children did not exit cleanly')
    elif states[0]['Result'] == 'success' or states[0]['ExecMainStatus'] == '0':
        raise ValueError('unexpected peer loss was not reported as head failure')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--action', choices=('graceful', 'peer-failure'), required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--restore-timer', required=True)
    args = parser.parse_args()
    if socket.gethostname() != 'spark-a183':
        parser.error('candidate lifecycle qualification runs only on the head')
    if re.fullmatch(r'b12x-flare-[a-z-]+restore-\d{8}T\d{6}Z\.timer', args.restore_timer) is None:
        parser.error('expected the exact pre-armed candidate restoration timer')
    running = command(0, ['systemctl', '--user', 'list-units', '--state=active,activating,deactivating',
                          '--type=service', '--no-legend', '--plain'])
    for line in running.splitlines():
        unit = line.split()[0]
        if unit == 'vllm-b12x.service' or (unit.startswith('b12x-flare-') and
                any(word in unit for word in ('bench', 'retrieval', 'memory-watch', 'prepare', 'qualify', 'restore'))):
            raise ValueError('conflicting client, memory enforcement or GPU unit: ' + unit)
    timers = command(0, ['systemctl', '--user', 'list-timers', '--no-legend', '--plain'])
    active = command(0, ['systemctl', '--user', 'show', args.restore_timer, '-p', 'ActiveState', '--value'])
    if active.strip() != 'active' or not any(args.restore_timer in line.split() for line in timers.splitlines()):
        raise ValueError('no scheduled candidate restoration timer observed')
    initial = [state(rank) for rank in (0, 1)]
    if any(s['ActiveState'] != 'active' for s in initial):
        raise ValueError('both candidate ranks must be active')
    invocations = [invocation_id(rank) for rank in (0, 1)]
    before = runtime_metrics(BASE)
    if any(before[name] for name in GAUGES):
        raise ValueError('other requests are active; lifecycle test refused')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x') as output:
        def emit(event, **data):
            output.write(json.dumps({'event': event, 'time': datetime.now(timezone.utc).isoformat(),
                                     **data}) + '\n')
            output.flush()

        emit('start', action=args.action, states=initial, invocations=invocations, metrics=before)
        finished = threading.Event()
        response_info = {}

        def consume():
            body = {'model': 'nvidia/GLM-5.3-Flash-FP4-Local', 'temperature': 1.0,
                    'top_p': .95, 'seed': 1234, 'max_tokens': 4096, 'stream': True,
                    'messages': [{'role': 'user', 'content': 'Write a long Python sorting tutorial.'}]}
            request = urllib.request.Request(BASE + '/v1/chat/completions', json.dumps(body).encode(),
                                             {'Content-Type': 'application/json'})
            try:
                chunks = 0
                with urllib.request.urlopen(request, timeout=30) as response:
                    for line in response:
                        chunks += line.startswith(b'data:')
                response_info.update(outcome='stream_closed', data_lines=chunks)
            except Exception as error:
                response_info.update(outcome='stream_interrupted', error_type=type(error).__name__)
            finally:
                finished.set()

        reader = threading.Thread(target=consume, daemon=True)
        reader.start()
        deadline = time.monotonic() + 120
        while not finished.is_set():
            during = runtime_metrics(BASE)
            generated = during['flare_generated_tokens_total'] - before['flare_generated_tokens_total']
            if generated >= 32 and during['flare_active_requests'] > 0:
                break
            if time.monotonic() >= deadline:
                raise ValueError('active decode was not observed within deadline')
            time.sleep(.1)
        else:
            raise ValueError('stream ended before sustained active decode')
        emit('trigger', generated_tokens=generated, metrics=during)
        started = time.monotonic()
        if args.action == 'graceful':
            command(0, ['systemctl', '--user', 'stop', '--no-block', UNITS[0]])
        else:
            command(1, ['systemctl', '--user', 'kill', '--kill-whom=all', '--signal=SIGKILL', UNITS[1]])
        deadline = started + 180
        while True:
            states = [state(rank) for rank in (0, 1)]
            if terminal(states) or time.monotonic() >= deadline:
                break
            time.sleep(1)
        emit('terminal', states=states, elapsed_s=time.monotonic() - started)
        reader.join(timeout=35)
        emit('request', finished=finished.is_set(), **response_info)
        # SIGKILL deliberately prevents the worker from writing a final record.
        native = [native_exit(rank, invocations[rank])
                  for rank in ((0, 1) if args.action == 'graceful' else (0,))]
        emit('native_exit', ranks=native)
        check_result(args.action, states, native)
        if not finished.is_set():
            raise ValueError('HTTP stream remained live after rank shutdown')
        # A free operation lock proves the supervised process groups released it.
        # Physical memory recovery is checked separately before the next GPU start.
        for rank in (0, 1):
            command(rank, ['flock', '-n', '/home/nvidia/b12x-flare/local/gpu-operation.lock', 'true'])
        emit('passed', action=args.action, operation_locks_released=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
