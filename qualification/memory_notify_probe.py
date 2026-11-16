"""CPU-only systemd readiness probe; synthetic memory, no GPU or cluster mutation."""
import sys
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0, '/home/nvidia/b12x-flare/scripts')
import flare_memory_watch as monitor

healthy = 'MemTotal: 134217728 kB\nMemFree: 104857600 kB\nMemAvailable: 104857600 kB\nSwapTotal: 0 kB\nSwapFree: 0 kB\n'
if sys.argv[1] == 'hang':
    import time
    monitor.notify_healthy({'violations': []}, False)
    time.sleep(30)
else:
    sys.argv = [sys.argv[0], '--out', sys.argv[2], '--seconds', '6']
    original = Path.read_text
    def read(path, *args, **kwargs):
        return healthy if str(path) == '/proc/meminfo' else original(path, *args, **kwargs)
    with patch.object(Path, 'read_text', read), patch.object(monitor.subprocess, 'run', return_value=SimpleNamespace(stdout=healthy)):
        raise SystemExit(monitor.main())
