#!/usr/bin/env python3
"""Render pinned Flare commands or inspect a Spark; never start/stop services."""

import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tomllib

GIB = 1 << 30
RECIPE = Path(__file__).resolve().parents[1] / "recipes/flare-glm53.json"


def load_recipe(path):
    recipe = json.loads(Path(path).read_text())
    for key in ("flare_revision", "flashinfer_revision", "checkpoint_revision"):
        value = recipe[key]
        if len(value) != 40 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError(f"{key} must be an immutable 40-character commit")
    root = Path(recipe["runtime_root"])
    if not root.is_absolute() or root == Path("/home/nvidia/b12x") or ".." in root.parts:
        raise ValueError("runtime_root must be an absolute isolated candidate directory")
    return recipe


def render(recipe, rank, core=None):
    """Return argv arrays and required files, not shell commands to evaluate."""
    root = Path(recipe["runtime_root"])
    source = root / "upstream/flare"
    config = root / "config.toml"
    uv = ["uv", "run", "--locked", "--extra", "prepare", "--extra", "test"]
    ignition = uv + ["ignition"]
    prepare_address = f'{recipe["head_address"]}:{recipe["prepare_port"]}'
    if rank == 0:
        prepare = ignition + [
            "export", "glm-5.3-flash", "--config", str(config),
            "--ranks", "2", "--rendezvous", prepare_address, "--gpus", "0",
            "--max-concurrency", str(recipe["concurrency"]),
            "--prefill-chunk-size", str(recipe["prefill_chunk"]),
            "--mtp-draft-tokens", str(recipe["mtp_drafts"]),
            "--no-mtp-adaptive-verification", "--no-context-parallel",
            "--language-model-only", "--compile-workers", str(recipe["compile_workers"]),
        ]
    else:
        prepare = ignition + ["join", prepare_address, "--config", str(config),
                              "--rank", "1", "--ranks", "2"]
    binary = source / "flare-cli/target/release/flare"
    serving = [str(binary), "run"]
    if rank == 0:
        if core is not None and not Path(core).is_absolute():
            raise ValueError("core must be an absolute path to the exported primary")
        serving += [core or "<EXPORTED_CORE_PRIMARY>"]
    serving += [
        "--rank", str(rank), "--rendezvous", f'{recipe["head_address"]}:{recipe["serve_port"]}',
        "--gpus", "0", "--host", "127.0.0.1", "--port", str(recipe["api_port"]),
        "--served-model-name", recipe["model"], "--max-concurrency", str(recipe["concurrency"]),
        "--mtp-draft-tokens", str(recipe["mtp_drafts"]), "--no-mtp-adaptive-verification",
        "--memory-limit", f'-{recipe["reserve_gib"]}G', "--kv-cache-limit", "memory",
        "--core-cache", str(root / "cores"), "--publisher-keys", str(root / "development-publisher.json"),
        "--trust-store", str(root / "trust.toml"), "--verify-weights",
    ]
    # JSON string quoting is valid TOML basic-string quoting for these paths.
    q = json.dumps
    config_text = (
        f'[paths]\nhub_cache = {q(recipe["hub_cache"])}\n'
        f'core_cache = {q(str(root / "cores"))}\nkernel_cache = {q(str(root / "kernels"))}\n'
        f'export_staging = {q(str(root / "staging"))}\n'
        f'[memory]\nreserve = "{recipe["reserve_gib"]}G"\n'
        f'[preparation]\ncompile_workers = {recipe["compile_workers"]}\n'
        f'checkpoint_token_file = {q(str(root / "checkpoint.token"))}\n'
    )
    return {
        "rank": rank, "cwd": str(source), "config_path": str(config), "config_toml": config_text,
        "build_env": {"BUILD_NVEP": "0", "FLASHINFER_BUILD_NO_PIP": "1", "CUTE_DSL_ARCH": "sm_121a"},
        "build": [["uv", "sync", "--locked", "--extra", "prepare", "--extra", "test"],
                  ["cargo", "build", "--release", "--locked", "--manifest-path", "flare-cli/Cargo.toml"]],
        "prepare": prepare, "serve": serving,
        "requirements": [
            "Both ranks must pass preflight before build/preparation; production must be stopped first.",
            "Create the same private preparation token on both hosts (at least 32 random bytes, mode 0600).",
            "Use the exact pinned source and dependency lockfiles on both hosts.",
            "After export, distribute the public development publisher profile to the peer.",
            "Review and approve the exact local-development signing fingerprint on both ranks before unattended serving.",
            "Serving commands are not a systemd lifecycle implementation; do not use them for a production window yet.",
        ],
    }


def command_output(argv):
    try:
        result = subprocess.run(argv, text=True, capture_output=True, timeout=15)
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def inspect_host(recipe, rank):
    """Read host facts without running GPU work, installing dependencies or changing services."""
    memory = {}
    if Path("/proc/meminfo").exists():
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, value = line.split(":", 1)
            if key in ("MemFree", "MemAvailable"):
                memory[key] = int(value.split()[0]) * 1024
    root = Path(recipe["runtime_root"])
    disk_path = root
    while not disk_path.exists():
        disk_path = disk_path.parent
    disk = shutil.disk_usage(disk_path)
    source = root / "upstream/flare"
    snapshot = Path(recipe["hub_cache"]) / "models--nvidia--GLM-5.3-Flash-FP4-Local/snapshots" / recipe["checkpoint_revision"]
    required_files = ["model.safetensors.index.json", "config.json", "tokenizer.json", "chat_template.jinja"]
    missing = [str(snapshot / name) for name in required_files if not (snapshot / name).is_file()]
    index = snapshot / "model.safetensors.index.json"
    if index.is_file():
        weight_map = json.loads(index.read_text()).get("weight_map", {})
        if not weight_map:
            missing.append("checkpoint weight_map is empty")
        for name in sorted(set(weight_map.values())):
            if not (snapshot / name).is_file():
                missing.append(str(snapshot / name))
    tools = {name: shutil.which(name) for name in ("uv", "cargo", "cmake", "ninja", "pkg-config", "protoc", "cc")}
    tools["nvcc"] = shutil.which("nvcc") or ("/usr/local/cuda/bin/nvcc" if Path("/usr/local/cuda/bin/nvcc").is_file() else None)
    native_packages = {name: command_output(["pkg-config", "--modversion", name]) for name in ("openssl", "liburing", "libibverbs", "python-3.12")}
    source_exists = source.is_dir()
    source_head = command_output(["git", "-C", str(source), "rev-parse", "HEAD"]) if source_exists else None
    source_dirty = command_output(["git", "-C", str(source), "status", "--porcelain"]) if source_exists else None
    lock_hashes = {name: hashlib.sha256((source / name).read_bytes()).hexdigest()
                   for name in ("uv.lock", "flare-cli/Cargo.lock", "heliopause/Cargo.lock") if (source / name).is_file()}
    dependency_pin = False
    if (source / "pyproject.toml").is_file() and (source / "uv.lock").is_file():
        project = tomllib.loads((source / "pyproject.toml").read_text())
        dependencies = project.get("project", {}).get("optional-dependencies", {}).get("prepare", [])
        expected = "https://github.com/local-inference-lab/flashinfer.git@" + recipe["flashinfer_revision"]
        lock = tomllib.loads((source / "uv.lock").read_text())
        dependency_pin = any(expected in dependency for dependency in dependencies) and any(
            package.get("name") == "flashinfer-python"
            and package.get("source", {}).get("git", "").endswith("#" + recipe["flashinfer_revision"])
            for package in lock.get("package", []))
    return {
        "hostname": platform.node(), "architecture": platform.machine(), "kernel": platform.release(),
        "rank": rank, "disk_path": str(disk_path), "disk_free_bytes": disk.free, "memory_bytes": memory,
        "tools": tools, "native_packages": native_packages,
        "cuda_compiler": command_output([tools["nvcc"], "--version"]) if tools["nvcc"] else None,
        "gpu_driver": command_output(["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"]),
        "incumbent_state": command_output(["systemctl", "--user", "is-active", "vllm-b12x.service"]),
        "checkpoint_missing": missing, "source_head": source_head, "source_dirty": source_dirty,
        "lock_sha256": lock_hashes, "flashinfer_pin_matches": dependency_pin,
    }


def blockers(recipe, facts):
    failures = []
    if facts["architecture"] != "aarch64":
        failures.append("native build requires Linux aarch64 on the Spark")
    minimum = recipe["head_disk_min_gib" if facts["rank"] == 0 else "worker_disk_min_gib"] * GIB
    if facts["disk_free_bytes"] < minimum:
        failures.append(f"free disk below conservative {minimum // GIB} GiB preparation budget")
    for key, minimum in (("MemFree", recipe["min_free_gib"]), ("MemAvailable", recipe["min_available_gib"])):
        if facts["memory_bytes"].get(key, 0) < minimum * GIB:
            failures.append(f"{key} below {minimum} GiB: build/preparation must wait")
    if facts["incumbent_state"] == "active":
        failures.append("incumbent service is active")
    for key, value in facts["tools"].items():
        if value is None:
            failures.append(f"missing build tool: {key}")
    for key, value in facts["native_packages"].items():
        if value is None:
            failures.append(f"missing pkg-config development package: {key}")
    if facts["source_head"] != recipe["flare_revision"] or facts["source_dirty"] != "":
        failures.append("candidate source is absent, dirty or not at the pinned Flare revision")
    if len(facts["lock_sha256"]) != 3:
        failures.append("candidate dependency lockfiles are incomplete")
    if not facts["flashinfer_pin_matches"]:
        failures.append("FlashInfer dependency declaration/lock do not match the candidate pin")
    if facts["checkpoint_missing"]:
        failures.append("checkpoint assets/shards are incomplete")
    if not facts["gpu_driver"] or "GB10" not in facts["gpu_driver"]:
        failures.append("GB10 driver identity unavailable")
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("render", "inspect", "preflight"))
    parser.add_argument("--recipe", type=Path, default=RECIPE)
    parser.add_argument("--rank", type=int, choices=(0, 1), required=True)
    parser.add_argument("--core")
    args = parser.parse_args()
    recipe = load_recipe(args.recipe)
    if args.action == "render":
        result = render(recipe, args.rank, args.core)
    else:
        result = inspect_host(recipe, args.rank)
        result["blockers"] = blockers(recipe, result)
    print(json.dumps(result, indent=2))
    return int(args.action == "preflight" and bool(result["blockers"]))


if __name__ == "__main__":
    sys.exit(main())
