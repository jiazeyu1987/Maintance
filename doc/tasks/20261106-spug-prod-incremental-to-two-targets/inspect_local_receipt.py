"""Read exact local receipt metadata, never dispatch or disclose credentials."""
import hashlib,json,subprocess
from common import TASK,PRIVATE,now,write,restore_kind
kind=restore_kind('58')
operation=json.loads((TASK/(kind+'-ui-submission.json')).read_text(encoding='utf8'))['request']['operationId']
digest=hashlib.sha256(operation.encode()).hexdigest()
script=r'''
import datetime,hashlib,json,pathlib
operation=OPERATION
digest=hashlib.sha256(operation.encode()).hexdigest()
root=pathlib.Path('/var/lib/intruoyi-spug/smallapp')
out={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'operationId':operation,'records':[]}
for name in [digest+'.json','ui/'+digest+'.json','terminal/'+digest+'.json']:
 p=root/name;v={'relativePath':name,'exists':p.exists()};out['records'].append(v)
 if p.is_file():
  raw=p.read_bytes();x=json.loads(raw)
  v.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),request=x.get('request'),
   spugHistoryId=x.get('spugHistoryId'),dispatchState=x.get('dispatchState'),dispatchErrorCode=x.get('dispatchErrorCode'),
   disposition=x.get('disposition'),reservedAt=x.get('reservedAt'),observedAt=x.get('observedAt'),
   lastState=x.get('lastResult',{}).get('state') if x.get('lastResult') else None)
print(json.dumps(out))
'''.replace('OPERATION',repr(operation))
docker='C:/Users/D01021/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe'
r=subprocess.run([docker,'exec','-i','f615a60c76f4','python3','-B','-'],input=script.encode(),capture_output=True,timeout=30)
if r.returncode:
 (PRIVATE/(kind+'-local-receipt-error.private.log')).write_bytes(r.stdout+r.stderr)
 raise RuntimeError('EXACT_LOCAL_RECEIPT_READ_FAILED')
out=json.loads(r.stdout);write(TASK/(kind+'-local-receipt.json'),out);print(json.dumps(out))
