import json
import subprocess
import sys
from pathlib import Path

base=Path('C:/SpugHandoff/release')
out=base/'private/intruoyi-fenbeitong-test-prod-20261125'
src=base/'source/ops/spug/release-center'
sys.path.insert(0,str(src))
from intruoyi_runtime import Runtime,ssh_source_bytes
c=json.loads((base/'executor.private.json').read_bytes())
r=Runtime(c)
state=json.loads((out/'state.private.json').read_text(encoding='utf-8'))
job=next(j for j in state['jobs'] if j['id']==sys.argv[1])
env=job['target']
assert env in ('test','prod')
p=r.profile(env)
p['stagingRoot']=job.get('runtimeStagingRoots',{}).get(env,p['stagingRoot'])
operations=[v['operationId'] for v in job.get('remoteOperations',[]) if v['action']=='deploy' and v['env']==env]
if not operations:
    print(json.dumps(dict(stage=job.get('currentStep'),deployment='not started')))
    raise SystemExit(0)
code=(src/'operation_journal.py').read_text(encoding='utf-8')+'\np='+repr(p)+'\nops='+repr(operations)+'\njob='+repr(job['id'])+'\ntag='+repr(job['releaseTag'])+'\n'
code+='''
from pathlib import Path
import subprocess
values=[inspect(p,value,job) for value in ops]
folder=Path(p['stagingRoot'])/tag
files=[dict(name=f.name,bytes=f.stat().st_size) for f in folder.iterdir() if f.is_file() and (f.name.startswith('recovery') or f.name=='deployment.json')]
containers={}
manifest=json.loads((folder/'manifest.json').read_text())
for role in ('backend','frontend'):
    result=subprocess.run(['docker','inspect',p[role]],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if result.returncode:containers[role]=dict(present=False);continue
    value=json.loads(result.stdout)[0]
    containers[role]=dict(running=value['State']['Running'],candidateImage=value['Image']==manifest['images'][role]['id'],
        startedAt=value['State'].get('StartedAt'),health=value['State'].get('Health',{}).get('Status'),restartCount=value.get('RestartCount'))
progress_path=folder/'deployment-progress.private.json'
progress=json.loads(progress_path.read_text()) if progress_path.is_file() else {}
workers=[]
for value in values:
    pid=value.get('pid')
    if not pid or value.get('worker')!='running':continue
    proc=Path('/proc')/str(pid)
    io={}
    for line in (proc/'io').read_text().splitlines():
        key,count=line.split(':',1)
        if key in ('rchar','wchar','read_bytes','write_bytes'):io[key]=int(count)
    workers.append(dict(pid=pid,comm=(proc/'comm').read_text().strip(),io=io))
print(json.dumps(dict(operations=[{k:v.get(k) for k in ('operationId','status','worker','startedAt','finishedAt')} for v in values],recoveryFiles=files,containers=containers,progress={k:progress.get(k) for k in ('phase','status','updatedAt')},workers=workers)))
'''
result=subprocess.run(['ssh',*r.ssh_options(),'root@'+p['host'],p['python']+' -'],input=ssh_source_bytes(code),capture_output=True,timeout=45)
assert result.returncode==0,'Read-only progress failed; do not replay deployment'
value=json.loads(result.stdout)
(out/(env+'-remote-progress.json')).write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(value))
