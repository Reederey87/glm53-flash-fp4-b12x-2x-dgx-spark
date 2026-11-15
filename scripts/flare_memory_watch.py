"""Sample both Spark memory pools; optionally enforce the registered serving gate."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import time

GIB = 1 << 30
FIELDS = {'MemTotal', 'MemFree', 'MemAvailable', 'SwapTotal', 'SwapFree'}


def memory(text):
    result = {}
    for line in text.splitlines():
        name, _, rest = line.partition(':')
        if name in FIELDS:
            value, unit = rest.split()
            if unit != 'kB' or int(value) < 0 or name in result:
                raise ValueError('invalid host memory observation')
            result[name] = int(value) * 1024
    if result.keys() != FIELDS or result['MemTotal'] <= 0:
        raise ValueError('incomplete host memory observation')
    if any(result[name] > result['MemTotal'] for name in ('MemFree', 'MemAvailable')):
        raise ValueError('host memory exceeds total')
    if result['SwapFree'] > result['SwapTotal']:
        raise ValueError('free swap exceeds total')
    return result


def violations(nodes):
    return [f'{node}:{key}' for node, values in nodes.items()
            for key, limit in (('MemFree', 3 * GIB // 2), ('MemAvailable', 8 * GIB))
            if values[key] < limit]


def queue_restore(unit):
    if re.fullmatch(r'b12x-flare-[a-z-]+restore-\d{8}T\d{6}Z\.service', unit) is None:
        raise ValueError('expected the exact pre-armed candidate restoration service')
    subprocess.run(['systemctl', '--user', 'start', '--no-block', unit], check=True, timeout=20)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--seconds', type=int, default=9000)
    parser.add_argument('--restore-unit', help='Enforce the gate by starting this pre-armed restore service')
    args = parser.parse_args()
    if args.seconds < 1 or args.seconds > 12000:
        parser.error('sampling duration must be 1..12000 seconds')
    if args.restore_unit and re.fullmatch(r'b12x-flare-[a-z-]+restore-\d{8}T\d{6}Z\.service', args.restore_unit) is None:
        parser.error('invalid restoration service name')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + args.seconds
    with args.out.open('x') as output:
        while time.monotonic() < deadline:
            sample = {'time': datetime.now(timezone.utc).isoformat(), 'nodes': {}}
            try:
                sample['nodes']['head'] = memory(Path('/proc/meminfo').read_text())
                remote = subprocess.run(['ssh', '-n', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5',
                                         'nvidia@192.168.177.11', 'cat', '/proc/meminfo'],
                                        text=True, capture_output=True, check=True, timeout=10)
                sample['nodes']['worker'] = memory(remote.stdout)
                sample['violations'] = violations(sample['nodes'])
            except (OSError, ValueError, subprocess.SubprocessError) as error:
                sample['observation_error'] = type(error).__name__
            output.write(json.dumps(sample) + '\n')
            output.flush()
            if args.restore_unit and (sample.get('violations') or sample.get('observation_error')):
                print('Memory qualification failed; queueing the pre-armed B12X restoration', flush=True)
                queue_restore(args.restore_unit)
                return 1
            time.sleep(5)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
