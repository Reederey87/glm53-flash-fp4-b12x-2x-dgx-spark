"""Linux user-systemd cancellation tests with ALL cluster/API commands mocked.

Run with uv on a Linux user manager. No GPU, production unit or API is touched.
Only uniquely named b12x-review-test-* transient units are managed for real.
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
IMAGE = "sha256:3b5da79c42ed4204440cfb07c6de1eba46441d5cba6b57d5428d44e60c10d0ed"


def real(*args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, text=True, **kwargs)


def wait_for(test, seconds=20):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if test():
            return
        time.sleep(.1)
    raise TimeoutError("test phase timed out")


def scenario(mode, signal, recovery_failure="none"):
    with tempfile.TemporaryDirectory(prefix="b12x-review-test-") as tmp:
        root = Path(tmp)
        out = root/"local/ab-20261110"
        out.mkdir(parents=True)
        (root/"scripts").mkdir()
        (root/"bin").mkdir()
        (root/"recipes").mkdir()
        for name in ("allocator_window.sh", "allocator_recover.sh"):
            text = (SCRIPTS/name).read_text().replace("/home/nvidia/.local/bin/uv", str(root/"bin/uv"))
            (root/"scripts"/name).write_text(text)
        (root/".env").write_text("B12X_ALLOCATOR_CONF=\n")
        recipe = root/"recipes/glm-5.3-flash-fp4-local.yaml"
        recipe.write_text("test fixture only\n")
        shutil.copy(recipe, out/"recipe.control.yaml")
        (out/"candidate.sha256").write_text(real("sha256sum", str(recipe)).stdout)
        (out/"control.log").write_text("5/5 checks passed hard\n")
        (out/"memory-a.csv.ready").write_text(f"fake-a {int(time.time())}\n")
        mock = r'''#!/bin/bash
set -eu
cd "$B12X_TEST_ROOT"
OUT="$B12X_TEST_ROOT/local/ab-20261110"
echo "$(basename "$0") $*" >> "$OUT/mock-events"
candidate() { [ "$(tail -n1 .env)" = 'B12X_ALLOCATOR_CONF=expandable_segments:True' ]; }
case "$(basename "$0")" in
 systemctl)
  case "$*" in
   *'show b12x-ab-a.service -p ActiveState'*) echo inactive ;;
   *'show b12x-ab-a.service -p Result'*) echo success ;;
   *'show b12x-ab-a.service -p ExecMainStatus'*) echo 0 ;;
   *'show b12x-ab-memory-a.service -p InvocationID'*) echo fake-a ;;
   *'show b12x-ab-memory-b.service -p InvocationID'*) echo fake-b ;;
   *'show vllm-b12x-watchdog'*|*'show vllm-b12x-tailscale'*) echo inactive ;;
   *'is-active --quiet b12x-ab-memory-b.service'*) test -f "$OUT/guard-active" ;;
   *'is-active'*) echo active ;;
   *'stop vllm-b12x-watchdog.timer '*)
    if [ "$B12X_TEST_MODE" = isolation ]; then
      touch "$OUT/phase"
      if [ "$B12X_TEST_ISOLATION_FAIL" = 1 ]; then exit 1; fi
      exec sleep 300
    fi ;;
   *'start vllm-b12x.service'*)
    if candidate && [ "$B12X_TEST_MODE" = startup ]; then touch "$OUT/phase"; exec sleep 300; fi ;;
   *'start vllm-b12x-tailscale.service'*)
    touch "$OUT/proxy-active"
    if [ "$B12X_TEST_RECOVERY" = proxy-failure ]; then exit 1; fi ;;
   *'stop vllm-b12x-tailscale.service'*) rm -f "$OUT/proxy-active" ;;
   *'stop '*|*'start '*) : ;;
   *) exit 99 ;;
  esac ;;
 systemd-run) touch "$OUT/guard-active"; echo "fake-b $(date +%s)" > "$OUT/memory-b.csv.ready" ;;
 docker)
  case "$*" in
   *'.Image'*) echo "$B12X_TEST_IMAGE" ;;
   *'.Config.Env'*) if candidate; then echo PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True; fi ;;
   'logs '*) echo 'GPU KV cache size: 2,350,210 tokens' ;;
   'top '*) echo 'mock rank argv' ;;
   *) exit 99 ;;
  esac ;;
 ssh) shift; exec /bin/bash -c "$*" ;;
 curl) : ;;
 uv)
  case "$*" in
   *smoke.py*)
    if ! candidate && [ "$B12X_TEST_RECOVERY" = hold-rollback ] && [ ! -e "$OUT/rollback-held-once" ]; then
      touch "$OUT/rollback-held-once" "$OUT/rollback-phase"; exec sleep 300
    fi
    echo '5/5 checks passed hard' ;;
   *compare_matrix.py*) echo 'mock receipt validator' ;;
   *allocator-b-probe*) : ;;
   *'--label allocator-b --out'*) touch "$OUT/phase"; exec sleep 300 ;;
   *) exit 99 ;;
  esac ;;
 *) exit 99 ;;
esac
'''
        for name in ("systemctl", "systemd-run", "docker", "ssh", "curl", "uv"):
            p = root/"bin"/name
            p.write_text(mock)
            p.chmod(0o755)
        unit = "b12x-review-test-" + uuid.uuid4().hex[:12]
        try:
            real("systemd-run", "--user", "--unit=" + unit,
                 "--property=KillMode=mixed", "--property=TimeoutStopSec=30",
                 "--property=ExecStopPost=/bin/bash " + str(root/"scripts/allocator_recover.sh"),
                 "--setenv=PATH=" + str(root/"bin") + ":/usr/bin:/bin",
                 "--setenv=B12X_TEST_ROOT=" + str(root), "--setenv=B12X_TEST_MODE=" + mode,
                 "--setenv=B12X_TEST_RECOVERY=" + recovery_failure,
                 "--setenv=B12X_TEST_ISOLATION_FAIL=" + ("1" if signal == "stop-failure" else "0"),
                 "--setenv=B12X_TEST_IMAGE=" + IMAGE,
                 "/bin/bash", str(root/"scripts/allocator_window.sh"))
            wait_for(lambda: (out/"phase").exists())
            if signal == "stop-failure":
                pass
            elif signal == "guard-failure":
                (out/"guard-active").unlink()
            else:
                real("/usr/bin/systemctl", "--user", "kill", "--kill-whom=main", "--signal=" + signal, unit)
            if recovery_failure == "hold-rollback":
                wait_for(lambda: (out/"rollback-phase").exists())
                real("/usr/bin/systemctl", "--user", "kill", "--kill-whom=main", "--signal=SIGKILL", unit)
            if recovery_failure == "proxy-failure":
                wait_for(lambda: real("/usr/bin/systemctl", "--user", "show", unit, "-p", "ActiveState", "--value").stdout.strip() in ("failed", "inactive"))
                assert not (out/"proxy-active").exists()
                assert (out/"recovery-required").exists()
                assert (out/"rollback-failed.txt").exists()
                return {"phase": mode, "failure": recovery_failure, "failed_closed": True}
            wait_for(lambda: (out/"recovery-success.txt").exists())
            wait_for(lambda: real("/usr/bin/systemctl", "--user", "show", unit, "-p", "ActiveState", "--value").stdout.strip() in ("failed", "inactive"))
            assert (root/".env").read_text().splitlines()[-1] == "B12X_ALLOCATOR_CONF="
            assert not (out/"recovery-required").exists()
            events = (out/"mock-events").read_text()
            assert 'start vllm-b12x-watchdog.timer' in events
            assert 'start vllm-b12x-tailscale.service' in events
            if signal != "SIGKILL" and recovery_failure != "hold-rollback":
                assert int((out/"primary-status.txt").read_text()) != 0
                assert int((out/"recovery-status.txt").read_text()) == 0
            return {"phase": mode, "failure": signal, "recovery_failure": recovery_failure, "restored": True}
        finally:
            subprocess.run(["/usr/bin/systemctl", "--user", "stop", unit], capture_output=True, timeout=40)
            subprocess.run(["/usr/bin/systemctl", "--user", "reset-failed", unit], capture_output=True)


if __name__ == "__main__":
    results = [scenario(mode, signal) for mode in ("startup", "measurement")
               for signal in ("SIGTERM", "SIGKILL", "guard-failure")]
    results += [scenario("measurement", "SIGTERM", failure) for failure in ("proxy-failure", "hold-rollback")]
    results += [scenario("isolation", signal) for signal in ("SIGTERM", "SIGKILL", "stop-failure")]
    print(json.dumps(results, indent=2))
