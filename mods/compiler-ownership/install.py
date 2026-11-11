"""Hash-pinned Python-only patch; no graph, tensor, dtype or kernel rewrite."""
import ast
import hashlib
import os
from pathlib import Path
import shutil
import tempfile

SOURCE_SHA256='668921c635ad810bfdb93a937ffa54a051859e5466cb8d941e1cb67e3e172e81'
TARGET=Path('/usr/local/lib/python3.12/dist-packages/vllm/v1/worker/gpu_worker.py')


def transform(source):
    anchor='logger = init_logger(__name__)\n'
    method='    def determine_available_memory(self) -> int:\n'
    if source.count(anchor)!=1 or source.count(method)!=1:raise ValueError('unexpected pinned worker shape')
    source=source.replace(anchor,'from vllm.v1.worker._b12x_compiler_ownership import observe_compiler_ownership\n\n'+anchor)
    source=source.replace(method,'    @observe_compiler_ownership\n'+method)
    ast.parse(source)
    return source


def install(target=TARGET):
    original=target.read_bytes()
    if hashlib.sha256(original).hexdigest()!=SOURCE_SHA256:raise ValueError('worker differs from pinned image')
    helper=target.with_name('_b12x_compiler_ownership.py')
    if helper.exists():raise ValueError('compiler diagnostic already installed; use fresh container')
    metadata=target.with_name('_b12x_compiler_metadata.py')
    if metadata.exists():raise ValueError('compiler metadata already installed')
    code=Path(__file__).with_name('observe.py').read_bytes();ast.parse(code)
    ast.parse(Path(__file__).with_name('metadata.py').read_bytes())
    changed=transform(original.decode()).encode()
    shutil.copyfile(Path(__file__).with_name('metadata.py'),metadata)
    shutil.copyfile(Path(__file__).with_name('observe.py'),helper)
    fd,temp=tempfile.mkstemp(prefix='.b12x-compiler-',dir=target.parent)
    try:
        with os.fdopen(fd,'wb') as stream:stream.write(changed)
        os.chmod(temp,target.stat().st_mode&0o777);os.replace(temp,target)
    finally:Path(temp).unlink(missing_ok=True)
    print('B12X_COMPILER_OWNERSHIP_INSTALLED patched='+hashlib.sha256(changed).hexdigest(),flush=True)


if __name__=='__main__':install()
