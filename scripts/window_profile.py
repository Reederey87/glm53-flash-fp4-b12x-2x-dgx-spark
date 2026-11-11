"""Read vLLM's actual /proc argv/env, or validate a retained profile. No torch."""
import argparse
import json
from pathlib import Path
import sys

FLAGS = ("--revision", "--tensor-parallel-size", "--node-rank", "--nnodes",
         "--max-model-len", "--max-num-seqs", "--max-num-batched-tokens",
         "--kv-cache-memory-bytes", "--kv-cache-dtype", "--quantization",
         "--moe-backend", "--linear-backend", "--attention-backend", "--load-format",
         "--block-size", "--reasoning-parser", "--tool-call-parser")


def inspect_proc():
    candidates = []
    for entry in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            argv = entry.read_bytes().decode().rstrip("\0").split("\0")
            if not any(Path(a).name == "vllm" and argv[i+1:i+2] == ["serve"] for i, a in enumerate(argv)):
                continue
            env = entry.with_name("environ").read_bytes().decode().split("\0")
        except (OSError, UnicodeError):
            continue
        flags = {}
        for flag in (*FLAGS, "--speculative-config"):
            if argv.count(flag) != 1:
                raise ValueError(f"missing/duplicate {flag}")
            flags[flag] = argv[argv.index(flag)+1]
        spec = json.loads(flags.pop("--speculative-config"))
        allocator = dict(item.split("=", 1) for item in env
                         if item.startswith(("PYTORCH_CUDA_ALLOC_CONF=", "PYTORCH_ALLOC_CONF=")))
        candidates.append({"pid": entry.parent.name, "flags": flags, "spec": spec,
                           "allocator": allocator,
                           "prefix_caching": "--enable-prefix-caching" in argv,
                           "chunked_prefill": "--enable-chunked-prefill" in argv})
    if not candidates:
        return None
    if len(candidates) != 1:
        raise ValueError("multiple vLLM serve processes")
    return candidates[0]


def validate(profile, backend, seats, rank, kv):
    expected = {"--revision": "76348ddb2be2e35e39ecfc00e75dc07703f4f3d5",
                "--tensor-parallel-size": "2", "--node-rank": str(rank), "--nnodes": "2",
                "--max-model-len": "1000000", "--max-num-seqs": str(seats),
                "--max-num-batched-tokens": "4096", "--kv-cache-memory-bytes": kv,
                "--kv-cache-dtype": "fp8", "--quantization": "modelopt_mixed",
                "--moe-backend": "b12x", "--linear-backend": "b12x",
                "--attention-backend": "B12X", "--load-format": "b12x", "--block-size": "256",
                "--reasoning-parser": "glm45", "--tool-call-parser": "glm47"}
    if profile["flags"] != expected:
        raise ValueError(f"profile flags do not match frozen controls: {profile['flags']}")
    spec = profile["spec"]
    if (spec.get("method") != "mtp" or spec.get("num_speculative_tokens") != 3
            or spec.get("moe_backend") != backend or spec.get("attention_backend") != "B12X"):
        raise ValueError(f"incorrect speculative configuration: {spec}")
    if profile["allocator"] or not profile["prefix_caching"] or not profile["chunked_prefill"]:
        raise ValueError("allocator/cache controls changed")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check")
    ap.add_argument("--backend")
    ap.add_argument("--seats", type=int)
    ap.add_argument("--rank", type=int)
    ap.add_argument("--kv", default="17G")
    args = ap.parse_args()
    if args.check:
        validate(json.loads(Path(args.check).read_text()), args.backend, args.seats, args.rank, args.kv)
        print("profile verified")
    else:
        profile = inspect_proc()
        if profile is None:
            sys.exit(3)
        print(json.dumps(profile, indent=2))
