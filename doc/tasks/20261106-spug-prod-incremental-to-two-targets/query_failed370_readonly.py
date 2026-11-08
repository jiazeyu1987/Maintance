"""Read the original failed operation through its authenticated GET endpoint."""
import json,urllib.request
from common import TASK,PRIVATE,now,write,restore_kind
kind=restore_kind('58');request=json.loads((TASK/(kind+'-ui-submission.json')).read_text(encoding='utf8'))['request']
saved=json.loads((PRIVATE/'spug-active-session.private.json').read_text(encoding='utf8'))
origin=next(v for v in saved['origins'] if v['origin']=='http://127.0.0.1:18080')
token=next(v['value'] for v in origin['localStorage'] if v['name']=='token')
endpoint='http://127.0.0.1:18080/backup-entry-api/operations/'+request['operationId']
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open(urllib.request.Request(endpoint,headers={'X-Token':token}),timeout=45) as response:
 assert response.status==200
 raw=response.read()
value=json.loads(raw);assert value['request']==request
assert value['result']['state']=='FAILED' and value['spugHistoryId']==370
destination=TASK/(kind+'-terminal-record.json');assert not destination.exists()
write(destination,value)
print(json.dumps(dict(observedAt=now(),operationId=request['operationId'],spugHistoryId=value['spugHistoryId'],
 state=value['result']['state'],errorCode=value['result']['errorCode'],authenticatedGet=True,businessWrites=0)))
