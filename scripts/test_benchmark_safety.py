"""Failure injection for evidence that must fail closed; CPU-only."""
import copy
import io
import json
import unittest
import os
from pathlib import Path
import subprocess
import tempfile
import time
from unittest.mock import patch

from compare_matrix import validate
from decode_bench import one_round, sse, SPEC, metrics

IDENTITY = {"head": ["1", "2", "3"], "worker": ["4", "5"]}


def stream(*, usage=True, done=True):
    chunks = [{"choices": [{"delta": {"reasoning": "thinking"}}]},
              {"choices": [{"delta": {}, "finish_reason": "length"}]}]
    if usage:
        chunks.append({"choices": [], "usage": {"completion_tokens": 200}})
    data = "".join("data: " + json.dumps(c) + "\n\n" for c in chunks)
    return io.BytesIO((data + ("data: [DONE]\n\n" if done else "")).encode())


def receipt():
    result = {"complete": True, "errors": [], "decode_budget": 200,
              "prefill": [], "decode": []}
    for c in (1, 2, 4, 8):
        for n in (8192, 16384, 32768, 65536, 131072):
            result["prefill"].append({"concurrency": c, "length": n, "requests": [
                {"prompt_tokens": n, "cached_tokens": 0, "prefill_tok_s": 2000.0, "ttft_s": n/2000.0} for _ in range(c)]})
        for rep in range(3):
            result["decode"].append({"concurrency": c, "rep": rep, "errors": [], "ok": c,
                "completion_tokens": 200*c, "drafts": 10, "draft_tokens": 30, "accepted": 20,
                "accept_rate": 2/3, "accept_length": 3, "aggregate_tok_s": 40,
                "metrics_before": {v:0 for v in SPEC.values()},
                "metrics_after": {SPEC["accepted"]:20, SPEC["draft_tokens"]:30, SPEC["drafts"]:10},
                "engine_before": IDENTITY, "engine_after": IDENTITY,
                "requests": [{"completion_tokens": 200, "ttft_s": .1, "decode_s": 5,
                              "done": True, "finish_reason": "length"} for _ in range(c)]})
    return result


class Safety(unittest.TestCase):
    def test_readiness_rejects_old_invocation_stale_and_future_time(self):
        text = Path(__file__).with_name("allocator_window.sh").read_text()
        function = text[text.index("guard_ok() {"):text.index("checked_run() {")]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mock = root/"systemctl"
            mock.write_text('#!/bin/bash\ncase "$*" in *InvocationID*) echo current;; *) exit 0;; esac\n')
            mock.chmod(0o755)
            env = {**os.environ, "PATH": str(root) + ":" + os.environ["PATH"], "OUT": str(root)}
            for token, age, valid in (("current", 0, True), ("previous", 0, False), ("current", 60, False), ("current", -60, False)):
                (root/"memory-a.csv.ready").write_text(f"{token} {int(time.time())-age}\n")
                r = subprocess.run(["bash", "-c", function + "\nguard_ok a"], env=env, capture_output=True)
                self.assertEqual(r.returncode == 0, valid)

    def test_guard_stops_service_on_bad_or_failed_probe(self):
        guard = Path(__file__).with_name("memory_guard.sh")
        for failure in ("malformed_head", "remote_failure"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                commands = {
                    "awk": "echo bad" if failure == "malformed_head" else "echo '3145728 3145728'",
                    "timeout": "exit 1",
                    "systemctl": 'echo "$*" >> "$GUARD_TEST_LOG"',
                }
                for name, code in commands.items():
                    p = root/name
                    p.write_text("#!/bin/bash\n" + code + "\n")
                    p.chmod(0o755)
                env = {**os.environ, "PATH": str(root) + ":" + os.environ["PATH"], "GUARD_TEST_LOG": str(root/"calls")}
                proc = subprocess.run(["bash", str(guard), str(root/"memory.csv")], env=env, capture_output=True, timeout=10)
                self.assertNotEqual(proc.returncode, 0)
                self.assertIn("stop vllm-b12x.service", (root/"calls").read_text())
                self.assertTrue((root/"memory.csv.abort").exists())
                self.assertFalse((root/"memory.csv.ready").exists())

    def test_stream_requires_done_and_usage(self):
        for usage, done in ((False, True), (True, False)):
            with self.subTest(usage=usage, done=done), patch("urllib.request.urlopen", return_value=stream(usage=usage, done=done)):
                with self.assertRaises(ValueError):
                    sse("http://test", {"max_tokens": 200})
        with patch("urllib.request.urlopen", return_value=stream()):
            self.assertEqual(sse("http://test", {"max_tokens": 200})["usage"]["completion_tokens"], 200)

    @patch("decode_bench.engine_identity", return_value=IDENTITY)
    def test_one_missing_request_usage_fails_batch(self, _identity):
        good = {"usage": {"completion_tokens": 200}, "first": 1.0, "end": 6.0,
                "ttft_s": .1, "done": True, "finish_reason": "length"}
        before = {v: 100 for v in SPEC.values()}
        after = {SPEC["accepted"]: 120, SPEC["draft_tokens"]: 130, SPEC["drafts"]: 110}
        with patch("decode_bench.sse", side_effect=[good, ValueError("missing usage")]), patch("decode_bench.metrics", side_effect=[before, after]):
            row = one_round("http://test", "model", 2, 200)
        self.assertEqual(row["ok"], 1)
        self.assertTrue(row["errors"])
        self.assertEqual(len(row["requests"]), 1)

    @patch("decode_bench.engine_identity", return_value=IDENTITY)
    def test_counter_reset_fails(self, _identity):
        good = {"usage": {"completion_tokens": 200}, "first": 1.0, "end": 6.0,
                "ttft_s": .1, "done": True, "finish_reason": "length"}
        with patch("decode_bench.sse", return_value=good), patch("decode_bench.metrics", side_effect=[{v:100 for v in SPEC.values()}, {v:0 for v in SPEC.values()}]):
            self.assertTrue(one_round("http://test", "model", 1, 200)["errors"])

    def test_reset_with_advancing_counters_is_caught_by_process_identity(self):
        good = {"usage": {"completion_tokens": 200}, "first": 1.0, "end": 6.0,
                "ttft_s": .1, "done": True, "finish_reason": "length"}
        changed = {"head": ["6", "7", "8"], "worker": ["9", "10"]}
        with patch("decode_bench.sse", return_value=good), patch("decode_bench.engine_identity", side_effect=[IDENTITY, changed]), patch("decode_bench.metrics", side_effect=[{v:100 for v in SPEC.values()}, {v:200 for v in SPEC.values()}]):
            self.assertIn("engine process identity changed during batch", one_round("http://test", "model", 1, 200)["errors"])

    def test_corrupt_receipts_fail(self):
        valid = receipt()
        validate(valid)
        for corruption in ("missing_usage", "missing_done", "negative_drafts", "nan_counter", "missing_cell", "cache_hit", "nan_prefill", "infinite_duration", "zero_rate", "wrong_ratio", "missing_snapshot", "changed_engine"):
            r = copy.deepcopy(valid)
            if corruption == "missing_usage": r["decode"][0]["requests"] = []
            if corruption == "missing_done": r["decode"][0]["requests"][0]["done"] = False
            if corruption == "negative_drafts": r["decode"][0]["drafts"] = -1
            if corruption == "nan_counter": r["decode"][0]["drafts"] = float("nan")
            if corruption == "missing_cell": r["prefill"].pop()
            if corruption == "cache_hit": r["prefill"][0]["requests"][0]["cached_tokens"] = 256
            if corruption == "nan_prefill": r["prefill"][0]["requests"][0]["prefill_tok_s"] = float("nan")
            if corruption == "infinite_duration": r["decode"][0]["requests"][0]["decode_s"] = float("inf")
            if corruption == "zero_rate": r["decode"][0]["aggregate_tok_s"] = 0
            if corruption == "wrong_ratio": r["decode"][0]["accept_rate"] = .5
            if corruption == "missing_snapshot": r["decode"][0]["metrics_before"] = {}
            if corruption == "changed_engine": r["decode"][0]["engine_after"] = {"head": ["6", "7", "8"], "worker": ["4", "5"]}
            with self.subTest(corruption=corruption), self.assertRaises(ValueError): validate(r)

    def test_metrics_requires_every_finite_counter(self):
        valid = "\n".join(f"{v} 100" for v in SPEC.values())
        for bad in ("", valid.replace(next(iter(SPEC.values())), "missing_counter"), valid.replace("100", "nan", 1), valid.replace("100", "oops", 1)):
            with patch("urllib.request.urlopen", return_value=io.BytesIO(bad.encode())):
                self.assertEqual(metrics("http://test"), {})
        with patch("urllib.request.urlopen", return_value=io.BytesIO(valid.encode())):
            self.assertEqual(len(metrics("http://test")), 3)


if __name__ == "__main__":
    unittest.main()
