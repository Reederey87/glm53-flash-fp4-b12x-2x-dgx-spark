"""Release completed candidate core file pages before the unchanged memory gate.

Linux POSIX_FADV_DONTNEED is advisory and does not delete file data. Flush first;
the following preflight still decides whether enough physical memory is free.
"""
import fcntl
import json
import os
from pathlib import Path
import pwd
import subprocess


def main():
    root = Path('/home/nvidia/b12x-flare')
    if pwd.getpwuid(os.getuid()).pw_name != 'nvidia':
        raise RuntimeError('run as the candidate owner nvidia')
    with (root / 'local/gpu-operation.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for rank in (0, 1):
            for phase in ('build', 'prepare', 'serve'):
                unit = f'b12x-flare{"" if phase == "serve" else "-" + phase}@{rank}.service'
                result = subprocess.run(['systemctl', '--user', 'show', unit, '-p', 'ActiveState', '--value'],
                                        check=True, capture_output=True, text=True)
                if result.stdout.strip() not in ('inactive', 'failed'):
                    raise RuntimeError(f'{unit} is not stopped')
        cores = root / 'cores'
        files, total = 0, 0
        for path in cores.rglob('*'):
            if path.is_symlink() or not path.is_file():
                continue
            if not path.resolve().is_relative_to(cores):
                raise RuntimeError(f'path escaped candidate cores: {path}')
            with path.open('rb') as file:
                before = os.fstat(file.fileno())
                os.fsync(file.fileno())
                os.posix_fadvise(file.fileno(), 0, 0, os.POSIX_FADV_DONTNEED)
                after = os.fstat(file.fileno())
                for field in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns'):
                    if getattr(before, field) != getattr(after, field):
                        raise RuntimeError(f'core changed during cache release: {path}')
                files += 1
                total += before.st_size
        print(json.dumps({'files': files, 'file_bytes_advised': total, 'data_deleted': False,
                          'memory_gate_still_required': True}))


if __name__ == '__main__':
    main()
