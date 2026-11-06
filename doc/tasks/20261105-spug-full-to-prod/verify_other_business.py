"""Compare every original definition and every unrelated runtime without exposing Env."""
import argparse,hashlib,json
from install_prod_control import PRIVATE,TASK,ROOT,remote

def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def snapshot(r):
    definition={k:r[k] for k in ['Path','Args','HostConfig','Config']}
    definition['Mounts']=sorted(r['Mounts'],key=lambda m:m['Destination'])
    return dict(image=r['Image'],definition=digest(definition),runtime=dict(state={k:r['State'][k] for k in ['Running','Paused','Restarting','Pid','StartedAt','FinishedAt']},restartCount=r['RestartCount'],networks=digest(r['NetworkSettings']['Networks'])))

SCRIPT=r'''
import datetime,hashlib,json,pathlib,subprocess
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def snapshot(r):
 definition={k:r[k] for k in ['Path','Args','HostConfig','Config']};definition['Mounts']=sorted(r['Mounts'],key=lambda m:m['Destination'])
 return dict(image=r['Image'],definition=digest(definition),runtime=dict(state={k:r['State'][k] for k in ['Running','Paused','Restarting','Pid','StartedAt','FinishedAt']},restartCount=r['RestartCount'],networks=digest(r['NetworkSettings']['Networks'])))
ids=subprocess.check_output(['/usr/bin/docker','ps','-aq','--no-trunc'],timeout=10).decode().split()
rows=json.loads(subprocess.check_output(['/usr/bin/docker','inspect',*ids],timeout=15));current={r['Id']:snapshot(r) for r in rows}
assert set(current)==set(EXPECTED),'CONTAINER_SET_CHANGED'
for identity,old in EXPECTED.items():
 now=current[identity]
 assert now['image']==old['image'] and now['definition']==old['definition'],'ORIGINAL_DEFINITION_CHANGED'
 if identity not in TARGET_IDS:assert now==old,'OTHER_BUSINESS_RUNTIME_CHANGED'
assert hashlib.sha256(pathlib.Path('/etc/fstab').read_bytes()).hexdigest()=='69fb0d75be5ff1c785d0680046757b5c536b9d29d12d1713ca752ee58ebc72b7','FSTAB_CHANGED'
assert hashlib.sha256((pathlib.Path(ROOT)/'installation.json').read_bytes()).hexdigest()=='8c64992e339d88f42f34ff6b13810943e5670c3cac1e34f3221a2dd1f9c38971','OLD_STAGE_CHANGED'
print(json.dumps(dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),allOriginalDefinitionsAndImagesPreserved=True,otherBusinessRuntimePreserved=True,otherBusinessContainerCount=len(current)-len(TARGET_IDS),fstabPreserved=True,originalStagePreserved=True)))
'''

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phase',required=True);args=parser.parse_args()
    assert args.phase in ['during-backup','before-restore','during-restore','retry-preflight','health-preflight','health-installed','after-restore','closeout']
    rows=json.loads((PRIVATE/'original-production.private.json').read_text(encoding='utf-8'))['containers']
    expected={r['Id']:snapshot(r) for r in rows}
    names={'/intruoyi-backend','/intruoyi-frontend','/intruoyi-mysql','/intruoyi-redis','/ragflow_compose-minio-1'}
    targets=[r['Id'] for r in rows if r['Name'] in names];assert len(targets)==5
    report=remote('EXPECTED='+repr(expected)+'\nTARGET_IDS='+repr(targets)+'\nROOT='+repr(ROOT)+'\n'+SCRIPT,45)
    (TASK/('other-business-'+args.phase+'.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
