"""Independently verify immutable package, actual images, metadata and JVM URLs."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

BASE=Path('C:/SpugHandoff/release')
OUT=BASE/'private/intruoyi-fenbeitong-test-prod-20261125'
SRC=BASE/'source/ops/spug/release-center'
sys.path.insert(0,str(SRC))
from intruoyi_runtime import Runtime,ssh_source_bytes
env,tag,commit,deployment_id,final_job_id=sys.argv[1:]
assert env in ('test','prod')
c=json.loads((BASE/'executor.private.json').read_text(encoding='utf-8-sig'))
r=Runtime(c)
p=r.profile(env)
state=json.loads((OUT/'state.private.json').read_text(encoding='utf-8'))
deploy=next(j for j in state['jobs'] if j['id']==deployment_id)
final=next(j for j in state['jobs'] if j['id']==final_job_id)
assert deploy['status']==final['status']=='succeeded' and deploy['releaseTag']==final['releaseTag']==tag
assert deploy['target']==env and final['technicalVerification']['status']=='passed'
package=next(v for v in state['packages'] if v['releaseTag']==tag)
folder=BASE/'state/packages'/tag
manifest_bytes=(folder/'manifest.json').read_bytes()
m=json.loads(manifest_bytes)
assert hashlib.sha256(manifest_bytes).hexdigest()==package['manifestSha256']
assert m['gitCommit']==commit and len(commit)==40
assert m['releaseTag']==m['IMAGE_TAG']==tag
observed=r.observe(env)
assert observed['releaseTag']==tag and observed['backendHealth']['status']=='UP'
assert observed['frontendHttpStatus']==200 and observed['maintenance'] is False and not observed.get('runtimeOpeningPending')
assert observed.get('backupSourceBindingPending') is not True
operations=[v for v in deploy.get('remoteOperations',[]) if v['action']=='deploy' and v['env']==env]
assert len(operations)==1
p['stagingRoot']=deploy.get('runtimeStagingRoots',{}).get(env,p['stagingRoot'])
code=(SRC/'operation_journal.py').read_text(encoding='utf-8')+'\np='+repr(p)+'\nm='+repr(m)+'\ntag='+repr(tag)+'\nop='+repr(operations[0]['operationId'])+'\njob='+repr(deployment_id)+'\n'
code+='''
import re,subprocess,urllib.request,shlex
from pathlib import Path
remote=inspect(p,op,job)
assert remote['status']=='succeeded', 'Remote deployment operation is not succeeded'
env_bytes=Path(p['runtimeEnvironmentFile']).read_bytes()
tags=re.findall(rb'(?m)^IMAGE_TAG=([^\\r\\n]*)',env_bytes)
assert tags==[tag.encode()], 'IMAGE_TAG mismatch'
images={}
for role in ('backend','frontend'):
    container=json.loads(subprocess.check_output(['docker','inspect',p[role]]))[0]
    image=json.loads(subprocess.check_output(['docker','image','inspect',m['images'][role]['name']]))[0]
    assert container['State']['Running'] and container['Image']==image['Id']==m['images'][role]['id']
    assert m['images'][role]['name'] in image['RepoTags']
    images[role]=dict(imageId=image['Id'],name=m['images'][role]['name'],running=True)
cmd=subprocess.check_output(['docker','exec',p['backend'],'cat','/proc/1/cmdline']).decode().split(chr(0))
public=[a for a in cmd if a.startswith('-Dyudao.erp.fenbeitong-assistant.public-url=')]
internal=[a for a in cmd if a.startswith('-Dyudao.erp.fenbeitong-assistant.assistant-host=')]
assert public==['-Dyudao.erp.fenbeitong-assistant.public-url='+p['fenbeitongAssistantUrl']], 'Actual JVM public URL mismatch'
assert internal==['-Dyudao.erp.fenbeitong-assistant.assistant-host='+p['fenbeitongAssistantHost']], 'Actual JVM internal host mismatch'
with urllib.request.urlopen(p['entryUrl'].rstrip('/')+'/release-info.json',timeout=30) as response:
    info=json.load(response)
assert info['releaseTag']==tag and info['sourceCommit']==m['gitCommit']
contracts=[]
directory=Path(p['stagingRoot'])/tag
for f in sorted(directory.glob('database-contract-*.json')):
    value=json.loads(f.read_text())
    contracts.append(value)
assert contracts and all(v['status']=='PASS' and v['releaseTag']==tag for v in contracts), 'Database contract failed or mismatched'
assert {v['phase'] for v in contracts}=={'after-migrations','before-backend-open','before-public-open'}, 'Required contract phase missing'
print(json.dumps(dict(images=images,IMAGE_TAG=tags[0].decode(),operationStatus=remote['status'],
    operationId=op,publicUrl=p['fenbeitongAssistantUrl'],internalHost=p['fenbeitongAssistantHost'],
    actualJvmVerified=True,frontendReleaseTag=info['releaseTag'],databaseContractReceipts=contracts)))
'''
result=subprocess.run(['ssh',*r.ssh_options(),'root@'+p['host'],p['python']+' -'],input=ssh_source_bytes(code),capture_output=True,timeout=90)
if result.returncode:
    (OUT/(env+'-runtime-error.private.txt')).write_bytes(result.stderr)
    raise SystemExit('Runtime validation failed; private exact diagnostic retained')
remote=json.loads(result.stdout)
report=dict(status='PASS',environment=env,releaseTag=tag,gitCommit=m['gitCommit'],packageSha256=package['packageSha256'],manifestSha256=package['manifestSha256'],deploymentJob=deployment_id,finalJob=final_job_id,operation='SUCCESS',backendHealth='UP',frontendHttpStatus=200,maintenance=False,runtimeOpeningPending=False,backupSourceBindingPending=False,technicalStatus='passed',**remote)
(OUT/(env+'-runtime-verification.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='databaseContractReceipts'},ensure_ascii=False))
