"""Candidate-only preparation/serving lifecycle; invoked by user systemd units."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import re
from pathlib import Path
import signal
import subprocess
import time
import urllib.request
import uuid

from flare_candidate import RECIPE, blockers, inspect_host, load_recipe, render, serving_reserve_gib
from flare_provenance import export_receipt, verify_export_receipt


def serving_recipe(recipe):
    """Read explicit serving arms from the append-only ledger without shell evaluation."""
    recipe = dict(recipe)
    ledger = Path(recipe["runtime_root"]) / ".env"
    values = {}
    if ledger.exists():
        for line in ledger.read_text().splitlines():
            name, sep, value = line.partition("=")
            if sep and name.strip() in {"FLARE_SERVE_RESERVE_GIB", "FLARE_SCHEDULER_POLICY",
                                       "FLARE_NATIVE_ARM", "FLARE_SCHEDULER_TRACE"}:
                values[name.strip()] = value.strip()
    for name, value in values.items():
        if name == "FLARE_SERVE_RESERVE_GIB":
            recipe["serve_reserve_gib"] = serving_reserve_gib(value)
        elif name == "FLARE_SCHEDULER_POLICY":
            if value not in ("balanced", "throughput", "latency"):
                raise ValueError("FLARE_SCHEDULER_POLICY must be balanced, throughput or latency")
            recipe["scheduler_policy"] = value
        elif name == "FLARE_NATIVE_ARM":
            if value != "upstream" and (len(value) != 64 or any(c not in "0123456789abcdef" for c in value)):
                raise ValueError("FLARE_NATIVE_ARM must be upstream or a manifest SHA256")
            recipe["native_arm"] = value
        elif name == "FLARE_SCHEDULER_TRACE":
            if value != "off" and re.fullmatch(r"[a-z0-9][a-z0-9.-]{0,100}\.jsonl", value) is None:
                raise ValueError("FLARE_SCHEDULER_TRACE must be off or a local JSONL filename")
            recipe["scheduler_trace"] = value
    return recipe


def verify_native_arm(recipe, command):
    """Verify an immutable host-policy binary without replacing the pinned exporter."""
    arm = recipe.get("native_arm", "upstream")
    if arm == "upstream":
        return
    root = Path(recipe["runtime_root"]).resolve()
    directory = root / "native" / arm
    manifest = directory / "manifest.json"
    binary = directory / "flare"
    if any(not path.resolve().is_relative_to(directory) for path in (manifest, binary)):
        raise ValueError("native arm files must remain in their immutable directory")
    if hashlib.sha256(manifest.read_bytes()).hexdigest() != arm:
        raise ValueError("native arm manifest digest mismatch")
    data = json.loads(manifest.read_text())
    if data.get("schema") != 1 or data.get("kind") != "prefill-latency":
        raise ValueError("unsupported native arm manifest")
    if data.get("flare_revision") != recipe["flare_revision"]:
        raise ValueError("native arm source revision mismatch")
    patch = root / "qualification/flare-prefill-latency.patch"
    if hashlib.sha256(patch.read_bytes()).hexdigest() != data.get("patch_sha256"):
        raise ValueError("native arm patch digest mismatch")
    trace_digest = data.get("trace_patch_sha256")
    if trace_digest is not None:
        trace_patch = root / "qualification/flare-scheduler-trace.patch"
        if hashlib.sha256(trace_patch.read_bytes()).hexdigest() != trace_digest:
            raise ValueError("native arm trace patch digest mismatch")
    if recipe.get("scheduler_trace", "off") != "off" and (not trace_digest or data.get("trace_schema") != 1):
        raise ValueError("native arm lacks the qualified trace contract")
    for name in ("helios/Cargo.lock", "flare-cli/Cargo.lock"):
        actual = hashlib.sha256((root / "upstream/flare" / name).read_bytes()).hexdigest()
        if data.get("lock_sha256", {}).get(name) != actual:
            raise ValueError("native arm dependency lock mismatch")
    if hashlib.sha256(binary.read_bytes()).hexdigest() != data.get("binary_sha256"):
        raise ValueError("native arm binary digest mismatch")
    if str(binary) != command[0]:
        raise ValueError("native arm executable path mismatch")


def serving_command(recipe, rank, state):
    root = Path(recipe["runtime_root"])
    profile = root / "development-publisher.json"
    if hashlib.sha256(profile.read_bytes()).hexdigest() != state["publisher_profile_sha256"]:
        raise ValueError("publisher profile changed after acceptance")
    entries = json.loads(profile.read_text())
    if len(entries) != 1 or entries[0]["namespace"] != "local-development":
        raise ValueError("expected the exact local development publisher")
    public = bytes(entries[0]["public_key"])
    if len(public) != 32 or hashlib.sha256(public).hexdigest() != state["key_fingerprint"]:
        raise ValueError("publisher key fingerprint mismatch")
    core = Path(state["core_primary"])
    if not core.is_absolute() or not core.resolve().is_relative_to(root / "cores"):
        raise ValueError("core must belong to the isolated candidate cache")
    if rank == 0 and hashlib.sha256(core.read_bytes()).hexdigest() != state["core_primary_sha256"]:
        raise ValueError("exported primary changed after acceptance")
    verify_export_receipt(recipe, state)
    command = render(recipe, rank, str(core))["serve"]
    verify_native_arm(recipe, command)
    return command + ["--offline", "--dangerously-approve-key", state["key_fingerprint"],
                      "--dangerously-accept-publisher", "local-development"]


def finish_child(child, root, action, rank, invocation, stopping):
    """Reap the actual native process and retain its result across unit collection."""
    forced = False
    if child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=60)
        except subprocess.TimeoutExpired:
            forced = True
            child.kill()
            child.wait()
    result = {'schema': 1, 'event': 'native_exit', 'action': action, 'rank': rank,
              'invocation_id': invocation, 'native_pid': child.pid,
              'native_returncode': child.returncode, 'shutdown_requested': stopping,
              'forced_kill': forced, 'time': datetime.now(timezone.utc).isoformat()}
    path = root / 'local' / f'native-exit-{action}-rank{rank}-{invocation}.json'
    temporary = path.with_suffix('.json.tmp')
    with temporary.open('x') as output:
        output.write(json.dumps(result) + '\n')
        output.flush()
        os.fsync(output.fileno())
    temporary.replace(path)
    print(json.dumps(result), flush=True)
    code = child.returncode
    return code if code >= 0 else 128 - code


def stop_peer(ssh, unit, allow_drain):
    """Match upstream's head-first shutdown and 30-second natural peer drain.

    A successful head exit does not mean peer resource teardown has finished.
    Sending the worker SIGTERM immediately can kill it before its coordinated
    exit. Failed heads still request immediate peer cleanup.
    """
    if allow_drain:
        started = time.monotonic()
        deadline = started + 30
        outcome = 'deadline'
        while (remaining := deadline - time.monotonic()) > 0:
            try:
                peer = subprocess.run(ssh + ['systemctl', '--user', 'show', unit,
                                            '--property=ActiveState', '--value'],
                                      text=True, capture_output=True,
                                      timeout=min(5, remaining))
            except subprocess.TimeoutExpired:
                outcome = 'probe_timeout'
                break
            if peer.returncode != 0:
                outcome = 'probe_failed'
                break
            if peer.stdout.strip() in ('inactive', 'failed'):
                outcome = peer.stdout.strip()
                break
            time.sleep(min(1, max(0, deadline - time.monotonic())))
        print(json.dumps({'event': 'peer_drain', 'unit': unit, 'outcome': outcome,
                          'elapsed_s': time.monotonic() - started}), flush=True)
    # Still clean up on a timeout or failed peer; its real native exit remains
    # authoritative and a forced/signal exit cannot pass the graceful gate.
    subprocess.run(ssh + ['systemctl', '--user', 'stop', unit], timeout=65, check=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "serve"))
    parser.add_argument("rank", type=int, choices=(0, 1))
    args = parser.parse_args()
    recipe = load_recipe(RECIPE)
    if args.action == "serve":
        recipe = serving_recipe(recipe)
    root = Path(recipe["runtime_root"])
    invocation = os.environ.get('INVOCATION_ID', uuid.uuid4().hex)
    if re.fullmatch(r'[0-9a-f]{32}', invocation) is None:
        raise ValueError('invalid service invocation ID')
    failures = blockers(recipe, inspect_host(recipe, args.rank))
    running = subprocess.check_output(["docker", "ps", "-q", "--filter", "name=^/vllm_node$"], text=True).strip()
    if failures or running:
        raise RuntimeError("candidate start refused: " + "; ".join(failures + (["incumbent container running"] if running else [])))
    subprocess.run(["sha256sum", "--check", str(root / "local/build.sha256")],
                   cwd=root / "upstream/flare", check=True)
    if args.action == "prepare":
        command = render(recipe, args.rank)["prepare"]
        # Dependencies have already been installed and verified by the build unit.
        command[2:7] = ["--no-sync"]  # replace --locked/extra prepare/extra test
    else:
        state = json.loads((root / "local/accepted-core.json").read_text())
        command = serving_command(recipe, args.rank, state)
    print(json.dumps({"action": args.action, "rank": args.rank, "argv": command}), flush=True)
    unit = ("b12x-flare-prepare@1.service" if args.action == "prepare" else "b12x-flare@1.service")
    ssh = ["ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "nvidia@" + recipe["worker_address"]]
    if args.rank == 0:
        subprocess.run(ssh + ["systemctl", "--user", "start", "--no-block", unit], check=True, timeout=20)
    child = None
    exit_code = None
    stopping = False
    export_log = None
    previous_primaries = set()
    if args.action == "prepare":
        if args.rank == 0:
            previous_primaries = {p.resolve() for p in (root / "cores/models").glob("**/model.safetensors")}
        log_path = root / "logs" / f"export-rank{args.rank}-{uuid.uuid4().hex}.log"
        export_log = log_path.open("x")
        print(f"Preparation output: {log_path}", flush=True)

    def stop(_signum, _frame):
        nonlocal stopping
        stopping = True
        if child is not None and child.poll() is None:
            child.terminate()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        output = {} if export_log is None else {"stdout": export_log, "stderr": subprocess.STDOUT}
        child = subprocess.Popen(command, cwd=root / "upstream/flare", **output)
        deadline = time.monotonic() + 900
        ready = False
        while not stopping and child.poll() is None:
            if args.rank == 0:
                try:
                    peer = subprocess.run(ssh + ["systemctl", "--user", "show", unit, "--property=ActiveState", "--value"],
                                          text=True, capture_output=True, timeout=20)
                except subprocess.TimeoutExpired:
                    if stopping:
                        break
                    raise
                # systemd sends SIGTERM to the whole control group. The peer
                # check can be interrupted while both ranks shut down normally.
                if stopping:
                    break
                if peer.returncode != 0 or peer.stdout.strip() in ("failed", "deactivating"):
                    raise RuntimeError("peer failed or became unreachable")
                if args.action == "serve":
                    if peer.stdout.strip() not in ("active", "activating"):
                        raise RuntimeError("serving peer exited")
                    if not ready:
                        try:
                            with urllib.request.urlopen(f'http://127.0.0.1:{recipe["api_port"]}/health', timeout=2) as response:
                                ready = response.status == 200
                        except OSError:
                            pass
                        if ready:
                            print("Candidate health HTTP 200; hardware qualification remains required", flush=True)
                        elif time.monotonic() > deadline:
                            raise RuntimeError("candidate readiness timed out")
            time.sleep(2)
        if args.action == "prepare" and args.rank == 0 and not stopping and child.returncode == 0:
            receipt = export_receipt(recipe, command, log_path, previous_primaries)
            receipt_path = root / "local" / (log_path.stem + ".json")
            receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
            print(f"Export provenance awaiting acceptance: {receipt_path}", flush=True)
    finally:
        try:
            if child is not None:
                exit_code = finish_child(child, root, args.action, args.rank, invocation, stopping)
        finally:
            try:
                if args.rank == 0:
                    stop_peer(ssh, unit, args.action == 'serve' and stopping and exit_code == 0)
            finally:
                if export_log is not None:
                    export_log.close()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
