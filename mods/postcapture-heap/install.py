"""Patch only the exact V2 capture method with a Python host-heap boundary."""
import ast
import hashlib
import os
from pathlib import Path
import shutil
import tempfile

SOURCE_SHA256 = 'aeadc5177c80789112c8e4836639b97e6fbb056711a4e6c81748c7ab9ad805d0'
TARGET = Path('/usr/local/lib/python3.12/dist-packages/vllm/v1/worker/gpu/model_runner.py')


def transform(source):
    anchor = 'logger = init_logger(__name__)\n'
    method = '    def capture_model(self, *, profile_only: bool = False) -> int:\n'
    if source.count(anchor) != 1 or source.count(method) != 1:
        raise ValueError('unexpected pinned V2 runner shape')
    source = source.replace(anchor, 'from vllm.v1.worker.gpu._b12x_postcapture_heap import return_heap_after_capture\n\n'+anchor)
    source = source.replace(method, '    @return_heap_after_capture\n'+method)
    ast.parse(source)
    return source


def install(target=TARGET):
    original = target.read_bytes()
    if hashlib.sha256(original).hexdigest() != SOURCE_SHA256:
        raise ValueError('V2 runner differs from pinned image')
    helper = target.with_name('_b12x_postcapture_heap.py')
    if helper.exists():
        raise ValueError('postcapture heap patch already installed')
    code = Path(__file__).with_name('return_heap.py'); ast.parse(code.read_bytes())
    shutil.copyfile(code, helper)
    changed = transform(original.decode()).encode()
    fd, temporary = tempfile.mkstemp(prefix='.b12x-postcapture-', dir=target.parent)
    try:
        with os.fdopen(fd, 'wb') as stream: stream.write(changed)
        os.chmod(temporary, target.stat().st_mode & 0o777); os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)
    print('B12X_POSTCAPTURE_HEAP_INSTALLED patched='+hashlib.sha256(changed).hexdigest(), flush=True)


if __name__ == '__main__': install()
