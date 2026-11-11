"""Hash-guarded, ephemeral loader instrumentation. Does not import vLLM/torch."""
import argparse
import ast
import hashlib
from pathlib import Path
import os
import shutil
import tempfile

SOURCE_SHA256 = "aa398e74ee835537403e60186f2e9a81e8741a4b35fec68b47df6537716a45b7"
TARGET = Path("/usr/local/lib/python3.12/dist-packages/vllm/model_executor/model_loader/utils.py")


def transform(source):
    def replace(old, new):
        nonlocal source
        if source.count(old) != 1:
            raise ValueError("pinned loader anchor missing or ambiguous: " + old[:70])
        source = source.replace(old, new)

    replace("    maybe_retie_word_embeddings(model, model_config)\n",
            "    from vllm.model_executor.model_loader._b12x_startup_trace import snapshot\n"
            "    snapshot('postload-enter', target_device)\n"
            "    maybe_retie_word_embeddings(model, model_config)\n")
    replace("            with loading_context:\n                quant_method.process_weights_after_loading(module)\n",
            "            snapshot('quant-before', target_device, name, type(quant_method).__name__)\n"
            "            with loading_context:\n                quant_method.process_weights_after_loading(module)\n"
            "            snapshot('quant-after', target_device, name, type(quant_method).__name__)\n")
    replace("            release_device_memory_under_pressure(target_device)\n",
            "            _b12x_released = release_device_memory_under_pressure(target_device)\n"
            "            snapshot('release-after', target_device, name, type(quant_method).__name__, _b12x_released)\n")
    replace("    for _, module in model.named_modules():\n",
            "    snapshot('attention-enter', target_device)\n"
            "    for _, module in model.named_modules():\n")
    replace("    # Model-level post-load hook, after the per-layer quant finalize.\n",
            "    snapshot('attention-exit', target_device)\n"
            "    # Model-level post-load hook, after the per-layer quant finalize.\n")
    replace("    # Needed for torchao model reloading via model.reload_weights\n",
            "    snapshot('postload-exit', target_device)\n"
            "    # Needed for torchao model reloading via model.reload_weights\n")
    ast.parse(source)
    return source


def install(target):
    original = target.read_bytes()
    if hashlib.sha256(original).hexdigest() != SOURCE_SHA256:
        raise ValueError("loader source differs from pinned image; refusing instrumentation")
    patched = transform(original.decode()).encode()
    helper = target.with_name("_b12x_startup_trace.py")
    if helper.exists():
        raise ValueError("trace helper already exists; use a fresh container")
    ast.parse(Path(__file__).with_name("trace.py").read_text())
    shutil.copyfile(Path(__file__).with_name("trace.py"), helper)
    # No process has imported this loader yet: mods run before the exec script.
    # Atomic replacement also avoids exposing partial Python source.
    fd, temp = tempfile.mkstemp(prefix=".b12x-trace-", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(patched)
        os.chmod(temp, target.stat().st_mode & 0o777)
        os.replace(temp, target)
    finally:
        Path(temp).unlink(missing_ok=True)
    print("B12X_STARTUP_TRACE_INSTALLED source=" + SOURCE_SHA256 +
          " patched=" + hashlib.sha256(patched).hexdigest(), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path, default=TARGET)
    args = parser.parse_args()
    install(args.target)
