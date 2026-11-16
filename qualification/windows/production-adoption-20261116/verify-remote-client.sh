#!/bin/bash
set -euo pipefail
control=/private/tmp/flare-production-client-20261116.sock
ssh -M -S "$control" -o ExitOnForwardFailure=yes -o BatchMode=yes -f -N -L 127.0.0.1:18081:100.125.23.98:8000 nvidia@spark-a183.local
trap 'ssh -S "$control" -O exit nvidia@spark-a183.local >/dev/null 2>&1 || true' EXIT
UV_CACHE_DIR=/private/tmp/b12x-uv-cache uv run --offline python - <<'PY'
import json,urllib.request
from pathlib import Path
from datetime import datetime,timezone
base='http://127.0.0.1:18081'
with urllib.request.urlopen(base+'/health',timeout=15) as response:assert response.status==200
body={'model':'nvidia/GLM-5.3-Flash-FP4-Local','messages':[{'role':'user','content':'Reply with the single word READY.'}],'max_tokens':256}
req=urllib.request.Request(base+'/v1/chat/completions',json.dumps(body).encode(),{'Content-Type':'application/json'})
with urllib.request.urlopen(req,timeout=90) as response: result=json.load(response)
assert result['usage']['completion_tokens']>0
assert 'READY' in result['choices'][0]['message'].get('content','').upper(),result
receipt={'time':datetime.now(timezone.utc).isoformat(),'transport':'Mac SSH tunnel -> head tailnet listener8000 -> Flare8001','health':200,'request':body,'response':result,'passed':True}
Path('/private/tmp/flare-production-remote-client.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('Remote client health and generation passed through the existing proxy over SSH.')
PY
