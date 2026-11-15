"""Candidate-only preparation/serving lifecycle; invoked by user systemd units."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import urllib.request

from flare_candidate import RECIPE, blockers, inspect_host, load_recipe, render


def serving_recipe(recipe):
    """Read only the serving-reserve arm from the append-only ledger, without shell evaluation."""
    recipe = dict(recipe)
    ledger = Path(recipe["runtime_root"]) / ".env"
    if ledger.exists():
        for line in ledger.read_text().splitlines():
            name, sep, value = line.partition("=")
            if sep and name.strip() == "FLARE_SERVE_RESERVE_GIB":
                value = value.strip()
                if not value.isascii() or not value.isdecimal() or int(value) < 1:
                    raise ValueError("FLARE_SERVE_RESERVE_GIB must be a positive integer")
                recipe["serve_reserve_gib"] = int(value)
    return recipe


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
    command = render(recipe, rank, str(core))["serve"]
    return command + ["--offline", "--dangerously-approve-key", state["key_fingerprint"],
                      "--dangerously-accept-publisher", "local-development"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "serve"))
    parser.add_argument("rank", type=int, choices=(0, 1))
    args = parser.parse_args()
    recipe = load_recipe(RECIPE)
    if args.action == "serve":
        recipe = serving_recipe(recipe)
    root = Path(recipe["runtime_root"])
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
    stopping = False

    def stop(_signum, _frame):
        nonlocal stopping
        stopping = True
        if child is not None and child.poll() is None:
            child.terminate()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        child = subprocess.Popen(command, cwd=root / "upstream/flare")
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
        return child.returncode if not stopping else 0
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=60)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        if args.rank == 0:
            subprocess.run(ssh + ["systemctl", "--user", "stop", unit], timeout=150, check=False)


if __name__ == "__main__":
    raise SystemExit(main())
