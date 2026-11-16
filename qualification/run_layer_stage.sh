#!/bin/bash
set -Eeuo pipefail
r=/home/nvidia/b12x-flare
rank=${1:?rank required}
out=${2:?new receipt directory required}
[[ $rank == 0 || $rank == 1 ]]
[[ $(id -un) == nvidia && $(uname -m) == aarch64 && ! -e $out ]]
source "$r/scripts/flare_env.sh"
exec 9>"$r/local/gpu-operation.lock"
flock -n 9
[[ -z $(docker ps -q --filter name='^/vllm_node$') ]]
! systemctl --user is-active --quiet "b12x-flare@$rank.service"
[[ $(sha256sum "$r/qualification/native/flare_heliopause.so" | cut -d ' ' -f1) == f394b9647f45664524cc1c5538dc67defca5948fa7456473f9668060a74efba4 ]]
mkdir "$out"
cd "$r/upstream/flare"
export CUDA_VISIBLE_DEVICES=0 FLARE_RUN_ROCE_TESTS=1
export FLARE_PINNED_SOURCE="$PWD"
export FLARE_TEST_RANK="$rank" FLARE_TEST_RENDEZVOUS=tcp://192.168.177.10:29680
export FLARE_GLM53_SNAPSHOT=/home/nvidia/.cache/huggingface/hub/models--nvidia--GLM-5.3-Flash-FP4-Local/snapshots/76348ddb2be2e35e39ecfc00e75dc07703f4f3d5
export FLARE_LAYER_DIAGNOSTIC_OUT="$out/repeatability"
export PYTHONPATH="$r/qualification/native:$r/qualification:$PWD"
uv run --offline --no-project --python "$r/upstream/flare/.venv/bin/python" python - "$out/environment.json" "$rank" <<'PY'
import importlib.metadata,json,sys
from pathlib import Path
import torch,flare_heliopause
source=json.loads(importlib.metadata.distribution('flashinfer-python').read_text('direct_url.json'))
assert source['vcs_info']['commit_id']=='4fd836dcda0998b875129aad76774ca073df10c8'
assert torch.cuda.get_device_capability()==(12,1) and torch.cuda.device_count()==1
assert flare_heliopause.__file__=='/home/nvidia/b12x-flare/qualification/native/flare_heliopause.so'
Path(sys.argv[1]).write_text(json.dumps({'rank':int(sys.argv[2]),'local_gpu':0,
 'flashinfer':source,'torch':torch.__version__,'gpu':torch.cuda.get_device_name(),
 'capability':[12,1],'extension':flare_heliopause.__file__},indent=2)+'\n')
PY
set +e
timeout --signal=TERM --kill-after=30s 3600 \
 uv run --offline --no-project --python "$r/upstream/flare/.venv/bin/python" python -m pytest \
 -x -q -s "$r/qualification/test_glm53_layer_stage_cuda.py" --junitxml="$out/diagnostic.xml"
status=$?
set -e
printf '%s\n' "$status" > "$out/pytest-exit.txt"
uv run --offline --no-project --python /usr/bin/python3 python - "$out" "$rank" <<'PY'
import json,sys,xml.etree.ElementTree as ET
from pathlib import Path
p=Path(sys.argv[1]);cases=ET.parse(p/'diagnostic.xml').findall('.//testcase')
bad=[c.attrib['name'] for c in cases if any(c.find(t) is not None for t in ('failure','error','skipped'))]
rows=[json.loads(x) for x in (p/'repeatability-1.jsonl').read_text().splitlines()]
complete=len(rows)==11 and rows[-1]=={'complete':True,'samples':9}
result={'rank':int(sys.argv[2]),'cases':len(cases),'bad_cases':bad,
 'pytest_exit':int((p/'pytest-exit.txt').read_text()),'diagnostic_complete':complete,
 'scope':'repeatability diagnostic; does not waive original assertion'}
(p/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
assert complete and len(cases)==1,result
PY
exit "$status"
