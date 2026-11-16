#!/bin/bash
# Run only in a separately guarded idle-cluster qualification window.
set -Eeuo pipefail
r=/home/nvidia/b12x-flare
out=${1:?new receipt directory required}
[[ $(id -un) == nvidia && $(uname -m) == aarch64 ]]
[[ ! -e $out ]]
source "$r/scripts/flare_env.sh"
exec 9>"$r/local/gpu-operation.lock"
flock -n 9
[[ -z $(docker ps -q --filter name='^/vllm_node$') ]]
! systemctl --user is-active --quiet b12x-flare@0.service
mkdir "$out"
cd "$r/upstream/flare"
export CUDA_VISIBLE_DEVICES=0 FLARE_RUN_CUDA_TESTS=1
export FLARE_PINNED_SOURCE="$PWD"
export FLARE_GLM53_SNAPSHOT=/home/nvidia/.cache/huggingface/hub/models--nvidia--GLM-5.3-Flash-FP4-Local/snapshots/76348ddb2be2e35e39ecfc00e75dc07703f4f3d5
export PYTHONPATH="$r/qualification/native:$r/qualification:$PWD"
sha256sum "$r/qualification/native/flare_heliopause.so" tests/recipes/test_glm53_mla_cuda.py > "$out/source.sha256"
[[ $(sha256sum "$r/qualification/native/flare_heliopause.so" | cut -d ' ' -f1) == f394b9647f45664524cc1c5538dc67defca5948fa7456473f9668060a74efba4 ]]
uv run --offline --no-project --python "$r/upstream/flare/.venv/bin/python" python - "$out/environment.json" <<'PY'
import importlib.metadata, json, sys
from pathlib import Path
import torch
import b12x
import flare_heliopause
assert flare_heliopause.__file__ == '/home/nvidia/b12x-flare/qualification/native/flare_heliopause.so'
d=importlib.metadata.distribution('flashinfer-python')
source=json.loads(d.read_text('direct_url.json'))
assert source['vcs_info']['commit_id']=='4fd836dcda0998b875129aad76774ca073df10c8',source
assert torch.cuda.get_device_capability()==(12,1)
Path(sys.argv[1]).write_text(json.dumps({'flashinfer':source,'b12x':b12x.__file__,
    'gpu':torch.cuda.get_device_name(),'capability':[12,1],'torch':torch.__version__},indent=2)+'\n')
PY
set +e
timeout --signal=TERM --kill-after=30s 2400 \
  uv run --offline --no-project --python "$r/upstream/flare/.venv/bin/python" python -m pytest \
  -q -s "$r/qualification/test_glm53_native_mla_cuda.py" --junitxml="$out/mla.xml"
status=$?
set -e
printf '%s\n' "$status" > "$out/pytest-exit.txt"
uv run --offline --no-project --python /usr/bin/python3 python - "$out" <<'PYEND'
import json,sys,xml.etree.ElementTree as ET
from pathlib import Path
p=Path(sys.argv[1]);cases=ET.parse(p/'mla.xml').findall('.//testcase')
bad=[c.attrib['name'] for c in cases if any(c.find(k) is not None for k in ('failure','error','skipped'))]
expected={f'test_native_dense_mla_replay[{mode}-{rows}-{overlap}]'
 for mode,rows,overlap in [('decode',1,True),('decode',2,True),('decode',1,False),('decode',2,False),('prefill',65,True),('prefill',4096,True)]}
passed=(len(cases)==6 and {c.attrib['name'] for c in cases}==expected and not bad
        and (p/'pytest-exit.txt').read_text().strip()=='0')
report={'cases':len(cases),'bad_cases':bad,'passed':passed,
        'scope':'TP2 rank1 MLA replay with native dense activations; not full-model equivalence'}
(p/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
assert passed,report
PYEND
exit "$status"
