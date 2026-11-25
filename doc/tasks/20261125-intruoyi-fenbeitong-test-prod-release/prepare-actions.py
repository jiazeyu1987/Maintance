import json
import sys
from pathlib import Path

out=Path('C:/SpugHandoff/release/private/intruoyi-fenbeitong-test-prod-20261125')
state=json.loads((out/'state.private.json').read_text(encoding='utf-8'))
build=next(j for j in state['jobs'] if j['id']==sys.argv[1])
assert build['status']=='succeeded'
tag=build['releaseTag']
assert tag==sys.argv[2]
payloads={
 'test-preflight':dict(operation='publish-test'),
 'test-publish':{},
 'prod-preflight':dict(operation='promote-prod'),
 'prod-promote':{},
}
for name,payload in payloads.items():
    payload.update(releaseTag=tag,requestId='intruoyi-fbt-'+tag+'-'+name+'-1')
    (out/(name+'.json')).write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
print(json.dumps(dict(status='PASS',releaseTag=tag,sourceCommit=build['payload']['commit'],inputs=list(payloads))))
