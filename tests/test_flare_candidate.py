import copy
import sys
from pathlib import Path
import tomllib
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from flare_candidate import GIB, RECIPE, blockers, load_recipe, render
from spec_metrics import COUNTERS, counter_delta, parse_counters


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.recipe = load_recipe(RECIPE)

    def test_render_is_offline_and_preserves_checkpoint_and_incumbent(self):
        with patch("subprocess.run", side_effect=AssertionError("render attempted execution")):
            head = render(self.recipe, 0, "/data/core/model.safetensors")
            peer = render(self.recipe, 1)
        config = tomllib.loads(head["config_toml"])
        self.assertEqual(config["paths"]["hub_cache"], self.recipe["hub_cache"])
        self.assertEqual(config["memory"]["reserve"], "4G")
        self.assertIn("export", head["prepare"])
        self.assertIn("join", peer["prepare"])
        self.assertIn("--language-model-only", head["prepare"])
        self.assertIn("--no-context-parallel", head["prepare"])
        self.assertNotIn("--mtp-only", head["prepare"])
        self.assertIn("/data/core/model.safetensors", head["serve"])
        self.assertNotIn("<EXPORTED_CORE_PRIMARY>", peer["serve"])
        self.assertNotIn("8000", head["serve"])
        self.assertNotIn("--dangerously-approve-key", head["serve"])

    def test_relative_core_rejected(self):
        with self.assertRaisesRegex(ValueError, "absolute"):
            render(self.recipe, 0, "relative/core")

    def ready_facts(self):
        return dict(architecture="aarch64", rank=0, disk_free_bytes=300 * GIB,
                    memory_bytes={"MemFree": 110 * GIB, "MemAvailable": 115 * GIB},
                    incumbent_state="inactive", tools={"uv": "/bin/uv"},
                    native_packages={"openssl": "3.0"},
                    source_head=self.recipe["flare_revision"], source_dirty="",
                    flashinfer_pin_matches=True,
                    lock_sha256={"uv.lock": "a", "flare-cli/Cargo.lock": "b", "heliopause/Cargo.lock": "c"},
                    checkpoint_missing=[], gpu_driver="NVIDIA GB10, 580.178.04")

    def test_live_head_is_rejected_before_preparation(self):
        facts = self.ready_facts()
        facts.update(disk_free_bytes=184 * GIB, incumbent_state="active",
                     memory_bytes={"MemFree": 3 * GIB, "MemAvailable": 2 * GIB})
        errors = blockers(self.recipe, facts)
        self.assertEqual(len(errors), 4)
        self.assertTrue(any("disk" in error for error in errors))
        self.assertTrue(any("active" in error for error in errors))

    def test_missing_dependency_and_dirty_source_rejected(self):
        facts = self.ready_facts()
        facts["tools"]["protoc"] = None
        facts["source_dirty"] = " M pyproject.toml"
        self.assertEqual(len(blockers(self.recipe, facts)), 2)
        self.assertEqual(blockers(self.recipe, self.ready_facts()), [])


class CounterTests(unittest.TestCase):
    def fixture(self, engine, **values):
        return {name: values.get(key, 0) for key, name in COUNTERS[engine].items()}

    def test_labelled_samples_and_timestamp(self):
        text = '\n'.join(f'{name}{{model="test model",engine="0"}} 3 12345\n'
                         f'{name}{{model="test model",engine="1"}} 4'
                         for name in COUNTERS["vllm"].values())
        self.assertEqual(set(parse_counters(text, "vllm").values()), {7})

    def test_missing_is_not_zero(self):
        with self.assertRaisesRegex(ValueError, "missing counters"):
            parse_counters("# no speculative metrics yet", "flare")

    def test_invalid_counter_is_rejected(self):
        name = COUNTERS["flare"]["accepted"]
        for value in ("NaN", "+Inf", "-1"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_counters(f"{name} {value}", "flare")

    def test_flare_delta_does_not_use_lifetime_rates(self):
        before = self.fixture("flare", accepted=1000, draft_tokens=3000, drafts=1000, rounds=1200)
        after = self.fixture("flare", accepted=1006, draft_tokens=3010, drafts=1004, rounds=1205)
        delta = counter_delta(before, after, "flare")
        self.assertEqual(1 + delta["accepted"] / delta["drafts"], 2.5)
        self.assertEqual(delta["accepted"] / delta["draft_tokens"], 0.6)
        self.assertEqual(delta["zero_draft_rounds"], 1)

    def test_reset_and_impossible_counts_rejected(self):
        zero = self.fixture("flare")
        good = self.fixture("flare", accepted=2, draft_tokens=3, drafts=1, rounds=1)
        with self.assertRaisesRegex(ValueError, "reset"):
            counter_delta(good, zero, "flare")
        bad = copy.copy(good)
        bad[COUNTERS["flare"]["accepted"]] = 4
        with self.assertRaisesRegex(ValueError, "exceed"):
            counter_delta(zero, bad, "flare")


if __name__ == "__main__":
    unittest.main()
