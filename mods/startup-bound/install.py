"""Apply after the passive startup-memory mod, inside a fresh container."""
import ast
import hashlib
import os
from pathlib import Path
import shutil
import tempfile

SOURCE_SHA256='bafdd73c286f691bf169eae4f55dd06edf45cf42134e0348fac35cd5ce88b27b'
TARGET=Path('/usr/local/lib/python3.12/dist-packages/vllm/model_executor/model_loader/utils.py')


def transform(source):
    anchor='def process_weights_after_loading(\n'
    if source.count(anchor)!=1: raise ValueError('ambiguous pinned postload definition')
    source=source.replace(anchor,
        'from vllm.model_executor.model_loader._b12x_startup_bound import bounded_postload\n\n'
        '@bounded_postload\n'+anchor)
    ast.parse(source)
    return source


def install(target=TARGET):
    original=target.read_bytes()
    if hashlib.sha256(original).hexdigest()!=SOURCE_SHA256:
        raise ValueError('startup bound requires exact traced loader; refusing patch')
    helper=target.with_name('_b12x_startup_bound.py')
    if helper.exists(): raise ValueError('bound already installed; use a fresh container')
    code=Path(__file__).with_name('bound.py').read_bytes(); ast.parse(code)
    changed=transform(original.decode()).encode()
    shutil.copyfile(Path(__file__).with_name('bound.py'),helper)
    fd,temp=tempfile.mkstemp(prefix='.b12x-bound-',dir=target.parent)
    try:
        with os.fdopen(fd,'wb') as stream: stream.write(changed)
        os.chmod(temp,target.stat().st_mode&0o777)
        os.replace(temp,target)
    finally: Path(temp).unlink(missing_ok=True)
    print('B12X_STARTUP_BOUND_INSTALLED patched='+hashlib.sha256(changed).hexdigest(),flush=True)


if __name__=='__main__': install()
