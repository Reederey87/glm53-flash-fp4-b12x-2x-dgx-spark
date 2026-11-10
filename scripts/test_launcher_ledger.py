"""Launcher regression tests for a real append-only ledger and absent ranks."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent


class Launcher(unittest.TestCase):
    def test_last_wins_without_executing_or_rewriting_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, output = root/"ledger", root/"derived"
            original = ("IMAGE=original\nB12X_ALLOCATOR_CONF=\n"
                        "# candidate\nIMAGE=unchanged\nB12X_ALLOCATOR_CONF=expandable_segments:True\n"
                        f"QUOTED='literal $(touch {root / 'executed'}) # = still literal'\n"
                        "# rollback\nB12X_ALLOCATOR_CONF=\n")
            source.write_text(original)
            subprocess.run(["bash", str(ROOT/"scripts/render_env.sh"), str(source), str(output)], check=True)
            self.assertEqual(source.read_text(), original)
            text = output.read_text()
            assignments = [line.split("=", 1) for line in text.splitlines() if line and not line.startswith("#")]
            self.assertEqual(len(assignments), len(dict(assignments)))
            self.assertEqual(dict(assignments)["B12X_ALLOCATOR_CONF"], "")
            self.assertEqual(dict(assignments)["IMAGE"], "unchanged")
            self.assertFalse((root/"executed").exists())
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            source.write_text("BROKEN LINE\n")
            bad = subprocess.run(["bash", str(ROOT/"scripts/render_env.sh"), str(source), str(output)])
            self.assertNotEqual(bad.returncode, 0)
            self.assertEqual(output.read_text(), text)

    def test_failed_inspect_newline_means_absent_on_both_nodes(self):
        text = (ROOT/"launch.sh").read_text()
        function = text[text.index("container_state() {"):text.index("do_stop() {")]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, body in {
                "docker": "printf '\\n'; exit 1",
                "ssh": 'shift 5; exec /bin/bash -c "$*"',
            }.items():
                script = root/name
                script.write_text("#!/bin/bash\n" + body + "\n")
                script.chmod(0o755)
            env = {**os.environ, "PATH": str(root) + ":" + os.environ["PATH"]}
            for node in ("head", "worker"):
                script = "CONTAINER_NAME=vllm_node\nWORKER_IP=mock\n" + function + f"\ncontainer_state {node}"
                value = subprocess.run(["bash", "-c", script], env=env, check=True, capture_output=True, text=True).stdout
                self.assertEqual(value, "absent\n")


if __name__ == "__main__":
    unittest.main()
