"""Find persistence identifiers in deployed code; emit no code literals or data."""
import json
import re
import subprocess

out={'serverWrites':False,'modules':[]}
paths=['backend/src/config.js','backend/src/routes.js','backend/src/store.js','backend/src/tenant-store.js','backend/src/services/tenant-store.js']
p=subprocess.run(['docker','exec','fenbeitong-assistant','find','backend/src','-maxdepth','3','-type','f'],capture_output=True,timeout=10)
assert p.returncode==0
available=p.stdout.decode('utf-8').splitlines()
selected=[p for p in available if any(w in p.lower() for w in ['store','state','persist','tenant','config']) and p.endswith('.js')]
for path in selected[:20]:
    p=subprocess.run(['docker','exec','fenbeitong-assistant','cat',path],capture_output=True,timeout=10)
    assert p.returncode==0
    code=p.stdout.decode('utf-8')
    words=['state.json','fenbeitong-tenants.sqlite','voucherRecords','syncedDocuments','syncBatches','operationLogs','writeFile','readFile','idempotencyKey','fenbeitong_tenants','app_key','access_token','bill_sign_key']
    out['modules'].append({'file':path,'lineCount':len(code.splitlines()),'references':[{'line':i,'identifiers':[w for w in words if w in line]} for i,line in enumerate(code.splitlines(),1) if any(w in line for w in words)][:60]})
print(json.dumps(out))
