"""Preserve History362 control evidence and inspect health metadata read-only."""
import base64
import hashlib
import json
from install_prod_control import remote, TASK, PRIVATE

OPERATION='smallapp-d7a963eb1e9a4c16826c92d5753b30c3'
SCRIPT=r'''
import base64,datetime,hashlib,json,pathlib,subprocess
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3')
operation=OPERATION_LITERAL
def pin(p):
 raw=pathlib.Path(p).read_bytes()
 return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
receipt=json.loads((root/'target-installation.json').read_bytes())
owner=json.loads(pathlib.Path(receipt['ownerConfigurationPin']['path']).read_bytes())
target=owner['targets'][receipt['targetConfigRef']]
result=json.loads((root/'recovery-operations'/operation/'worker-result.json').read_bytes())
assert result['state']=='FAILED_RETAINED' and result['failureCode']=='ACTUAL_CONTAINER_HEALTHCHECK_REQUIRED' and result['actualExitCode']==1
assert result['data']['mutationDispatched'] is True
exited=json.loads((root/'recovery-operations'/operation/'child-exit.json').read_bytes())
assert exited['actualExitCode']==1 and exited['timedOut'] is False
active=pathlib.Path('/var/lib/spug-restore-resources/active.json')
assert json.loads(active.read_bytes())['operationId']==operation
services={s['role']:s for s in target['services']}
rows=json.loads(subprocess.check_output(['docker','inspect']+[s['id'] for s in target['services']],timeout=15))
states=[]
for row in rows:
 role=next(k for k,v in services.items() if v['id']==row['Id'])
 check=row['Config'].get('Healthcheck')
 states.append(dict(role=role,id=row['Id'],image=row['Image'],running=row['State']['Running'],pid=row['State']['Pid'],startedAt=row['State']['StartedAt'],
  dockerHealthcheckConfigured=isinstance(check,dict) and bool(check),dockerHealthcheckSha256=hashlib.sha256(json.dumps(check,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
  dockerHealthStatePresent=isinstance(row['State'].get('Health'),dict),dockerHealthStatus=row['State'].get('Health',{}).get('Status')))
secret_ref=target['secrets']['mysql']['MYSQL_ROOT_PASSWORD']
secret=pathlib.Path(secret_ref['path']).read_bytes()
assert len(secret)==secret_ref['bytes'] and hashlib.sha256(secret).hexdigest()==secret_ref['sha256']
assert secret and not any(c in secret for c in (b'\n',b'\r',b'\0'))
shell='test -z "${MYSQL_TEST_LOGIN_FILE:-}"; test -n "${HOME:-}"; test ! -e "$HOME/.mylogin.cnf"; test ! -L "$HOME/.mylogin.cnf"; IFS= read -r MYSQL_PWD; export MYSQL_PWD; exec "$@"'
sql='SELECT @@server_uuid,@@GLOBAL.read_only,@@GLOBAL.super_read_only,@@GLOBAL.event_scheduler,(SELECT COUNT(*) FROM information_schema.innodb_trx);'
state=subprocess.check_output(['docker','exec','-i',services['mysql']['id'],'sh','-ec',shell,'healthcheck-failure-diagnosis','mysql','--no-defaults','--protocol=SOCKET','--host=localhost','--batch','--skip-column-names','-e',sql],input=secret+b'\n',timeout=15).decode().strip().split('\t')
assert len(state)==5
files=[];copies={};excluded_count=0;excluded_bytes=0
for area in ('ledger','recovery-operations','replacement-state'):
 for p in sorted((root/area/operation).rglob('*')):
  if not p.is_file() or p.is_symlink():continue
  if p.suffix not in ('.json','.jsonl','.log'):
   excluded_count+=1;excluded_bytes+=p.stat().st_size;continue
  assert p.stat().st_size<=32*1024*1024,'CONTROL_EVIDENCE_FILE_TOO_LARGE'
  raw=p.read_bytes();files.append(dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
  copies[str(p.relative_to(root))]=base64.b64encode(raw).decode()
print(json.dumps(dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),operationId=operation,
 originalState=result['state'],failureCode=result['failureCode'],actualExitCode=1,finishedAt=result['finishedAt'],mutationDispatched=True,
 services=states,database=dict(uuid=state[0],readOnly=int(state[1]),superReadOnly=int(state[2]),eventScheduler=state[3],activeTransactions=int(state[4])),
 evidencePins=files,originalCopies=copies,excludedWorkingFileCount=excluded_count,excludedWorkingBytes=excluded_bytes,
 excludedWorkingFilesUntouched=True,activePointerPin=pin(active),ownerConfigurationPin=receipt['ownerConfigurationPin'],controlConfigurationPin=receipt['controlConfigurationPin'],sourceCommit=receipt['sourceCommit'])))
'''

if __name__ == '__main__':
    report_path=TASK/'healthcheck-failure-diagnosis.json'
    assert not report_path.exists(),'DIAGNOSIS_ALREADY_CAPTURED'
    report=remote(SCRIPT.replace('OPERATION_LITERAL',repr(OPERATION)),timeout=90)
    copies=report.pop('originalCopies')
    destination=PRIVATE/'failed-restore-362-originals'
    destination.mkdir(exist_ok=True)
    for name,data in copies.items():
        path=destination/name
        assert path.resolve().is_relative_to(destination.resolve())
        raw=base64.b64decode(data)
        path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists():assert path.read_bytes()==raw
        else:path.write_bytes(raw)
        assert hashlib.sha256(path.read_bytes()).hexdigest()==hashlib.sha256(raw).hexdigest()
    report['privateOriginalCopiesVerified']=len(copies)
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='evidencePins'}))
