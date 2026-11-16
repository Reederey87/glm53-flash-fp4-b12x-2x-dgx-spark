#!/bin/bash
# Run only in a separately guarded idle-cluster qualification window.
set -Eeuo pipefail
r=/home/nvidia/b12x-flare
test_root=${1:?immutable extracted FlashInfer test tree required}
out=${2:?new receipt directory required}
[[ $(id -un) == nvidia && $(uname -m) == aarch64 ]]
[[ ! -e $out ]]
[[ $test_root == "$r"/qualification/flashinfer-4fd836dcda0998b875129aad76774ca073df10c8 ]]
source "$r/scripts/flare_env.sh"
exec 9>"$r/local/gpu-operation.lock"
flock -n 9
[[ -z $(docker ps -q --filter name='^/vllm_node$') ]]
! systemctl --user is-active --quiet b12x-flare@0.service
! systemctl --user is-active --quiet b12x-flare@1.service
mkdir "$out"
cd "$test_root"
sha256sum --check source.sha256 > "$out/source-check.txt"
export CUDA_VISIBLE_DEVICES=0
export PYTHONPATH="$test_root"
uv run --offline --no-project --python "$r/upstream/flare/.venv/bin/python" python - "$out/environment.json" <<'PY'
import importlib.metadata, json, sys
from pathlib import Path
import torch
import b12x
d=importlib.metadata.distribution('flashinfer-python')
source=json.loads(d.read_text('direct_url.json'))
assert source['vcs_info']['commit_id']=='4fd836dcda0998b875129aad76774ca073df10c8',source
assert torch.cuda.get_device_capability()==(12,1)
Path(sys.argv[1]).write_text(json.dumps({'flashinfer':source,'b12x':b12x.__file__,
    'gpu':torch.cuda.get_device_name(),'capability':[12,1],'torch':torch.__version__},indent=2)+'\n')
PY
# These unchanged upstream tests cover both activation modes and poisoned replay.
# The unrelated two-local-GPU launcher-ownership case is not selected or claimed.
set +e
timeout --signal=TERM --kill-after=30s 2400 \
  uv run --offline --no-project --python "$r/upstream/flare/.venv/bin/python" python -m pytest \
  --confcutdir=tests/experimental/b12x -q -s \
  tests/experimental/b12x/moe/test_w4a16_a4_prefill.py::test_declared_csf_precision_replays_after_scale_scratch_poisoning \
  tests/experimental/b12x/moe/test_w4a16_a4_prefill.py::test_a4_prefill_matches_float64_emulation \
  tests/experimental/b12x/moe/test_nvfp4_csf.py::test_native_expert_output_and_shared_scratch_poisoned_replay \
  tests/experimental/b12x/moe/test_nvfp4_csf.py::test_a16_expanded_scales_reuse_the_planned_launch_for_live_counts \
  --junitxml="$out/expert-numerics.xml"
status=$?
set -e
printf '%s\n' "$status" > "$out/pytest-exit.txt"
uv run --offline --no-project --python /usr/bin/python3 python - "$out" <<'PY'
import json,sys,xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
p=Path(sys.argv[1]);cases=ET.parse(p/'expert-numerics.xml').findall('.//testcase')
counts=Counter(c.attrib['name'].split('[')[0] for c in cases)
expected={'test_declared_csf_precision_replays_after_scale_scratch_poisoning':8,
          'test_a4_prefill_matches_float64_emulation':21,
          'test_native_expert_output_and_shared_scratch_poisoned_replay':24,
          'test_a16_expanded_scales_reuse_the_planned_launch_for_live_counts':1}
bad=[c.attrib['name'] for c in cases if any(c.find(k) is not None for k in ('failure','error','skipped'))]
report={'cases':len(cases),'counts':dict(counts),'bad_cases':bad,
        'passed':dict(counts)==expected and not bad and (p/'pytest-exit.txt').read_text().strip()=='0',
        'scope':'SM121 component arithmetic/replay; not full-model equivalence'}
(p/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
assert report['passed'],report
PY
exit "$status"
