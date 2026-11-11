"""CPU-only validation: pinned transform, passive snapshots and trace evidence."""
import ast
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch, mock_open

from startup_trace_receipt import summarize, MARKER

ROOT = Path(__file__).resolve().parent.parent
MEMINFO = "MemTotal: 125829120 kB\nMemFree: 20971520 kB\nMemAvailable: 25165824 kB\nCached: 8388608 kB\nSReclaimable: 1024 kB\n"
def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/f"mods/startup-memory/{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StartupTrace(unittest.TestCase):
    def test_wrong_source_fails_before_mutation(self):
        installer = load("install")
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)/"utils.py"
            target.write_text("# wrong image\n")
            with self.assertRaises(ValueError): installer.install(target)
            self.assertEqual(target.read_text(), "# wrong image\n")
            self.assertFalse(target.with_name("_b12x_startup_trace.py").exists())

    def test_snapshot_is_passive_and_preserves_results(self):
        trace = load("trace")
        accelerator = types.SimpleNamespace(memory_allocated=lambda d:100,
            memory_reserved=lambda d:200,max_memory_allocated=lambda d:150)
        torch = types.SimpleNamespace(accelerator=accelerator,
            cuda=types.SimpleNamespace(is_initialized=lambda:True))
        platform = types.SimpleNamespace(current_platform=types.SimpleNamespace(is_integrated_gpu=lambda i:True))
        device = types.SimpleNamespace(type="cuda", index=0)
        with patch.object(trace,"installation",return_value={"loader_sha256":"loader","helper_sha256":"helper"}), patch.dict(sys.modules, {"torch":torch,"vllm.platforms":platform}), patch("builtins.open",mock_open(read_data=MEMINFO)), patch.object(trace.os,"write") as write:
            trace.snapshot("release-after", device, "model.layers.0.mlp.experts", "quant", True)
        record = json.loads(write.call_args.args[1].decode().split(MARKER)[1])
        self.assertEqual((record["allocated"],record["reserved"],record["releasable"]),(100,200,100))
        self.assertIs(record["released"],True)
        self.assertIs(record["integrated"],True)
        # These are all accelerator attributes supplied; any synchronization,
        # cache clearing, tensor allocation or peak reset would raise here.

    def test_require_initialized_worker(self):
        trace=load("trace")
        with patch.dict(sys.modules,{"torch":types.SimpleNamespace(cuda=types.SimpleNamespace(is_initialized=lambda:False)),
                "vllm.platforms":types.SimpleNamespace(current_platform=None)}):
            with self.assertRaises(RuntimeError): trace.snapshot("x",types.SimpleNamespace(type="cuda"))

    def test_missing_or_mixed_trace_rejected(self):
        with self.assertRaises(ValueError): summarize("no records",True)
        trace=load("trace"); writes=[]
        accelerator=types.SimpleNamespace(memory_allocated=lambda d:100,memory_reserved=lambda d:200,max_memory_allocated=lambda d:150)
        with patch.object(trace,"installation",return_value={"loader_sha256":"loader","helper_sha256":"helper"}), patch("builtins.open",mock_open(read_data=MEMINFO)), patch.dict(sys.modules,{"torch":types.SimpleNamespace(accelerator=accelerator,cuda=types.SimpleNamespace(is_initialized=lambda:True)),
                "vllm.platforms":types.SimpleNamespace(current_platform=types.SimpleNamespace(is_integrated_gpu=lambda i:True))}), patch.object(trace.os,"write",side_effect=lambda fd,data:writes.append(data.decode())):
            trace.snapshot("postload-enter",types.SimpleNamespace(type="cuda",index=0))
            trace.snapshot("quant-before",types.SimpleNamespace(type="cuda",index=0),"layer0","quant")
            trace.snapshot("quant-after",types.SimpleNamespace(type="cuda",index=0),"layer0","quant")
            trace.snapshot("release-after",types.SimpleNamespace(type="cuda",index=0),"layer0","quant",False)
            trace.snapshot("attention-enter",types.SimpleNamespace(type="cuda",index=0))
            trace.snapshot("attention-exit",types.SimpleNamespace(type="cuda",index=0))
            trace.snapshot("postload-exit",types.SimpleNamespace(type="cuda",index=0))
        result=summarize("".join(writes),True,"loader","helper")
        self.assertEqual(len(result["records"]),7)
        with self.assertRaises(ValueError): summarize("".join(writes),True,"wrong","helper")
        with self.assertRaises(ValueError): summarize("".join(writes[:2]+writes[3:]),True,"loader","helper")
        with self.assertRaises(ValueError): summarize(writes[0],True,"loader","helper")
        mixed = json.loads(writes[1].split(MARKER)[1]); mixed['pid']+=1
        with self.assertRaises(ValueError): summarize(writes[0]+MARKER+json.dumps(mixed))

    def test_recipe_changes_only_mods_and_recovers_canonical(self):
        control=(ROOT/"recipes/glm-5.3-flash-fp4-local.yaml").read_text()
        observed=(ROOT/"recipes/observations/startup-memory.yaml").read_text()
        self.assertEqual(control.replace("env:\n","mods:\n  - /home/nvidia/b12x/mods/startup-memory\n\nenv:\n",1),observed)
        config=(ROOT/"recipes/windows/startup-memory.conf").read_text()
        self.assertIn("WINDOW_KIND=observation",config)
        self.assertIn("RECOVERY_RECIPE=recipes/glm-5.3-flash-fp4-local.yaml",config)
        self.assertIn("RECOVERY_GUARD=1",config)


if __name__ == "__main__": unittest.main()
