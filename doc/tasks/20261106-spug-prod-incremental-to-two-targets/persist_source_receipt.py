"""Persist the independently verified installation without altering old records."""
import json
from common import TASK,remote,write
receipt=json.loads((TASK/'source-control-installation.json').read_text(encoding='utf-8'))
assert receipt['status']=='PASS' and receipt['readOnlyCompletionCheck']
script=r'''
import hashlib,json,os,pathlib,subprocess
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
for field in ('controlConfigurationPin','ownerConfigurationPin','dropinPin'):
 pin=RECEIPT[field];raw=pathlib.Path(pin['path']).read_bytes()
 assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'],'INSTALLATION_CHANGED'
assert int(subprocess.check_output(['systemctl','show',RECEIPT['service'],'-p','MainPID','--value']))==RECEIPT['pid'],'PID_CHANGED'
destination=pathlib.Path(RECEIPT['controlConfigurationPin']['path']).parent/('installation-incremental-'+RECEIPT['sourceCommit'][:7]+'.json')
fd=os.open(destination,os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_WRONLY,0o600)
with os.fdopen(fd,'wb') as out:out.write(canonical(RECEIPT));out.flush();os.fsync(out.fileno())
assert destination.read_bytes()==canonical(RECEIPT)
print(json.dumps(dict(status='PASS',path=str(destination),sha256=hashlib.sha256(destination.read_bytes()).hexdigest())))
'''
value=remote('172.30.30.57','RECEIPT='+repr(receipt)+'\n'+script)
write(TASK/'source-control-remote-receipt.json',value);print(json.dumps(value))
