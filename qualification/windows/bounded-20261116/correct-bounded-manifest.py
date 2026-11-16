# One-time provenance correction before any serving; preserve original artifact.
import hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
root=Path('/home/nvidia/b12x-flare');w=root/'local/bounded-window-20261116T041500Z'
lab=root/'local/bounded-scheduler-20261116T041500Z'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
state=subprocess.check_output(['systemctl','--user','show','b12x-flare-bounded-build-20261116T041500Z.service','-p','MainPID','-p','ExecMainCode','-p','ExecMainStatus'],text=True)
assert set(state.splitlines())=={'MainPID=0','ExecMainCode=1','ExecMainStatus=0'},state
artifact=json.loads((lab/'artifact.json').read_text());old=root/'native'/artifact['arm']
assert sha(old/'manifest.json')==artifact['arm']
m=json.loads((old/'manifest.json').read_text())
assert m['kit_commit']=='0c8f805c1a767b186ec6f2c95bb3ea6268490b6a'
expected=json.loads((w/'source-inputs.json').read_text())
assert expected['kit_commit']=='0c8f805fae82b768591fc908a936a7efec672234'
assert all(m[k]==v for k,v in expected['inputs'].items())
assert sha(old/'flare')==m['binary_sha256']==artifact['binary_sha256']
for name,digest in m['lock_sha256'].items(): assert sha(lab/name)==digest
assert subprocess.check_output(['git','-C',str(lab),'rev-parse','HEAD'],text=True).strip()==m['flare_revision']
m['kit_commit']=expected['kit_commit']
m['provenance_correction']={'original_manifest_sha256':artifact['arm'],'reason':'Corrected transcribed source commit before serving; tested inputs and binary unchanged.'}
data=(json.dumps(m,indent=2,sort_keys=True)+'\n').encode();arm=hashlib.sha256(data).hexdigest()
dest=root/'native'/arm;dest.mkdir(exist_ok=False)
shutil.copyfile(old/'flare',dest/'flare.tmp');os.chmod(dest/'flare.tmp',0o755)
(dest/'manifest.json.tmp').write_bytes(data)
os.replace(dest/'flare.tmp',dest/'flare');os.replace(dest/'manifest.json.tmp',dest/'manifest.json')
assert sha(dest/'flare')==m['binary_sha256']
(w/'artifact-corrected.json').write_text(json.dumps({'arm':arm,'binary_sha256':m['binary_sha256']})+'\n')
(w/'provenance-correction.json').write_text(json.dumps({'original_arm':artifact['arm'],'corrected_arm':arm,'kit_commit':m['kit_commit'],'binary_unchanged':True,'input_hashes_verified':expected['inputs']},indent=2)+'\n')
print((w/'provenance-correction.json').read_text())
