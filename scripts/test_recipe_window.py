"""CPU-only guards against measuring an unintended recipe or rank."""
import copy
from pathlib import Path
import unittest

from window_profile import validate

ROOT = Path(__file__).resolve().parent.parent


def profile(backend="humming", rank=0):
    return {"flags": {"--revision": "76348ddb2be2e35e39ecfc00e75dc07703f4f3d5",
        "--tensor-parallel-size": "2", "--node-rank": str(rank), "--nnodes": "2",
        "--max-model-len": "1000000", "--max-num-seqs": "4",
        "--max-num-batched-tokens": "4096", "--kv-cache-memory-bytes": "17G",
        "--kv-cache-dtype": "fp8", "--quantization": "modelopt_mixed",
        "--moe-backend": "b12x", "--linear-backend": "b12x",
        "--attention-backend": "B12X", "--load-format": "b12x", "--block-size": "256",
        "--reasoning-parser": "glm45", "--tool-call-parser": "glm47"},
        "spec": {"method": "mtp", "num_speculative_tokens": 3, "moe_backend": backend,
                 "attention_backend": "B12X"}, "allocator": {},
        "prefix_caching": True, "chunked_prefill": True}


class RecipeWindow(unittest.TestCase):
    def test_candidate_changes_only_draft_backend(self):
        a = (ROOT/"recipes/glm-5.3-flash-fp4-local.yaml").read_text()
        b = (ROOT/"recipes/candidates/draft-b12x.yaml").read_text()
        self.assertEqual(a.count('"moe_backend":"humming"'), 1)
        self.assertEqual(a.replace('"moe_backend":"humming"', '"moe_backend":"b12x"'), b)

    def test_valid_profiles_on_both_ranks(self):
        for backend in ("humming", "b12x"):
            for rank in (0, 1):
                validate(profile(backend, rank), backend, 4, rank, "17G")

    def test_wrong_treatment_or_controls_fail(self):
        for change in ("backend", "rank", "kv", "depth", "allocator", "cache", "seats"):
            p = copy.deepcopy(profile("b12x"))
            if change == "backend": p["spec"]["moe_backend"] = "humming"
            if change == "rank": p["flags"]["--node-rank"] = "1"
            if change == "kv": p["flags"]["--kv-cache-memory-bytes"] = "19G"
            if change == "depth": p["spec"]["num_speculative_tokens"] = 5
            if change == "allocator": p["allocator"] = {"PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"}
            if change == "cache": p["prefix_caching"] = False
            if change == "seats": p["flags"]["--max-num-seqs"] = "8"
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate(p, "b12x", 4, 0, "17G")


if __name__ == "__main__":
    unittest.main()
