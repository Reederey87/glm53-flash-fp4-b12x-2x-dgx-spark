"""Wrap the reviewed pinned-return worker; preserve its code and inner order."""
import ast
import hashlib
import os
from pathlib import Path
import shutil
import tempfile

SOURCE_SHA256 = 'ea6dc50f79cea69ab42d0fe31982a301b1081aa5f3f79eb268edb4df943b143e'
TARGET = Path('/usr/local/lib/python3.12/dist-packages/vllm/v1/worker/gpu_worker.py')


def transform(source):
    anchor = 'logger = init_logger(__name__)\n'
    decorator = '    @release_after_explicit_profile\n'
    if source.count(anchor) != 1 or source.count(decorator) != 1:
        raise ValueError('unexpected pinned-return worker shape')
    source = source.replace(anchor, 'from vllm.v1.worker._b12x_native_ownership import observe_native_owners_terminal\n\n' + anchor)
    source = source.replace(decorator, '    @observe_native_owners_terminal\n' + decorator)
    ast.parse(source)
    return source


def install(target=TARGET):
    original = target.read_bytes()
    if hashlib.sha256(original).hexdigest() != SOURCE_SHA256:
        raise ValueError('requires exact pinned-return worker input')
    for name in ('_b12x_native_ownership.py', '_b12x_native_metadata.py'):
        if target.with_name(name).exists():
            raise ValueError('native inventory already installed; use fresh container')
    changed = transform(original.decode()).encode()
    for source, name in (('observe.py', '_b12x_native_ownership.py'), ('metadata.py', '_b12x_native_metadata.py')):
        path = Path(__file__).with_name(source); ast.parse(path.read_bytes())
        shutil.copyfile(path, target.with_name(name))
    fd, temp = tempfile.mkstemp(prefix='.b12x-native-', dir=target.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(changed)
        os.chmod(temp, target.stat().st_mode & 0o777); os.replace(temp, target)
    finally:
        Path(temp).unlink(missing_ok=True)
    print('B12X_NATIVE_OWNERSHIP_INSTALLED patched=' + hashlib.sha256(changed).hexdigest(), flush=True)


if __name__ == '__main__':
    install()
