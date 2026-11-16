import hashlib,json,sys
from pathlib import Path
from datetime import datetime,timezone
rank=int(sys.argv[1]); policy=sys.argv[2]; arm=sys.argv[3]; expected=sys.argv[4]; reserve=sys.argv[5]
assert reserve in ('4', '3.875')
assert len(arm)==64 and all(c in '0123456789abcdef' for c in arm)
r=Path('/home/nvidia/b12x-flare'); binary=r/'native'/arm/'flare'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
assert sha(binary.parent/'manifest.json')==arm
manifest=json.loads((binary.parent/'manifest.json').read_text());assert manifest['binary_sha256']==expected
found=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:args=[x.decode() for x in (p/'cmdline').read_bytes().split(b'\0') if x]
 except (OSError,UnicodeDecodeError):continue
 if args and args[0]==str(binary):found.append((p,args))
assert len(found)==1,len(found)
p,args=found[0]
assert sha(r/'scripts/flare_run.py') == '8487477a39531194002fd429474c77ad1cffc37f2dab531ccf9b1dd1a8d509f3'
assert sha(r/'scripts/flare_candidate.py') == 'f3401039506fc8e4d3a30ef8cff90784b61e3abbf607e86609b3d660873a128e'
for name,wanted in {'--rank':str(rank),'--scheduler-policy':policy,'--memory-limit':f'-{reserve}G','--max-concurrency':'4','--mtp-draft-tokens':'3'}.items():assert args[args.index(name)+1]==wanted,(name,args)
assert '--verify-weights' in args and '--no-mtp-adaptive-verification' in args
assert '--scheduler-trace' not in args
assert sha(p/'exe')==expected
result={'time':datetime.now(timezone.utc).isoformat(),'rank':rank,'pid':int(p.name),'manifest':arm,'binary_sha256':expected,'policy':policy,'trace':False,'reserve_gib':float(reserve),'slots':4,'mtp_drafts':3}
if rank==0:
 state=json.loads((r/'local/accepted-core.json').read_text());core=Path(args[2]);assert str(core)==state['core_primary']
 assert sha(core)==state['core_primary_sha256']=='2c47847a8fa28aa375af499973e5d8f8a7259136b0b3347a1fcf7b4fb711d0c6'
 result['core_primary_sha256']=state['core_primary_sha256']
print(json.dumps(result))
