"""Preserve the failed original and read exact MAIN database state, without writes."""
import hashlib
import json
from install_prod_control import remote, TASK, PRIVATE

SCRIPT=r'''
import base64,datetime,hashlib,json,pathlib,subprocess
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3')
operation=OPERATION_LITERAL
def pin(p):
 raw=p.read_bytes()
 return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
receipt=json.loads((root/'target-installation.json').read_bytes())
owner=json.loads(pathlib.Path(receipt['ownerConfigurationPin']['path']).read_bytes())
target=owner['targets'][receipt['targetConfigRef']]
services={s['role']:s for s in target['services']}
secret_pin=target['secrets']['mysql']['MYSQL_ROOT_PASSWORD']
secret=pathlib.Path(secret_pin['path']).read_bytes()
assert len(secret)==secret_pin['bytes'] and hashlib.sha256(secret).hexdigest()==secret_pin['sha256']
assert secret and not any(c in secret for c in (b'\n',b'\r',b'\0'))
shell='test -z "${MYSQL_TEST_LOGIN_FILE:-}"; test -n "${HOME:-}"; test ! -e "$HOME/.mylogin.cnf"; test ! -L "$HOME/.mylogin.cnf"; IFS= read -r MYSQL_PWD; export MYSQL_PWD; exec "$@"'
def query(sql):
 return subprocess.check_output(['docker','exec','-i',services['mysql']['id'],'sh','-ec',shell,'failed-restore-diagnosis','mysql','--no-defaults','--protocol=SOCKET','--host=localhost','--batch','--skip-column-names','-e',sql],input=secret+b'\n',timeout=15).decode().strip()
state=query('SELECT @@server_uuid, @@GLOBAL.read_only, @@GLOBAL.super_read_only, (SELECT COUNT(*) FROM information_schema.innodb_trx), @@GLOBAL.event_scheduler;').split('\t')
database={'uuid':state[0],'readOnly':int(state[1]),'superReadOnly':int(state[2]),'activeTransactions':int(state[3]),'eventScheduler':state[4]}
database['tableCount']=int(query("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='"+target['database']+"';"))
database['enabledApplicationEvents']=int(query("SELECT COUNT(*) FROM information_schema.EVENTS WHERE EVENT_SCHEMA='"+target['database']+"' AND STATUS='ENABLED';"))
names=query('SHOW DATABASES;').splitlines()
database['onlySystemAndRegisteredApplication']=set(names)=={'information_schema','mysql','performance_schema','sys',target['database']}
database['schemaCount']=len(names)
rows=json.loads(subprocess.check_output(['docker','inspect']+[s['id'] for s in target['services']],timeout=15))
service_states=[dict(role=next(k for k,v in services.items() if v['id']==r['Id']),id=r['Id'],image=r['Image'],running=r['State']['Running'],pid=r['State']['Pid'],startedAt=r['State']['StartedAt']) for r in rows]
files=[];copies={}
for area in ('ledger','recovery-operations','replacement-state'):
 for p in sorted((root/area/operation).rglob('*')):
  if not p.is_file() or p.is_symlink():continue
  assert p.stat().st_size<=32*1024*1024,'FAILURE_FILE_TOO_LARGE'
  raw=p.read_bytes();reference=dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
  files.append(reference);copies[str(p.relative_to(root))]=base64.b64encode(raw).decode()
active=pathlib.Path('/var/lib/spug-restore-resources/active.json')
assert active.is_file()
pointer=json.loads(active.read_bytes());assert pointer['operationId']==operation
result=json.loads((root/'recovery-operations'/operation/'worker-result.json').read_bytes())
assert result['state']=='FAILED_RETAINED' and result['failureCode']=='FORMAL_SQL_DATABASE_CHANGED' and result['actualExitCode']==1
assert result['data']['mutationDispatched'] is True
exited=json.loads((root/'recovery-operations'/operation/'child-exit.json').read_bytes())
assert exited['actualExitCode']==1 and exited['timedOut'] is False
print(json.dumps(dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),operationId=operation,database=database,services=service_states,failureCode=result['failureCode'],actualExitCode=1,mutationDispatched=True,activePointerPin=pin(active),evidencePins=files,originalCopies=copies,ownerConfigurationPin=receipt['ownerConfigurationPin'],controlConfigurationPin=receipt['controlConfigurationPin'])))
'''

if __name__=='__main__':
    operation=json.loads((TASK/'restore-ui-submission.json').read_text(encoding='utf-8'))['request']['operationId']
    report=remote(SCRIPT.replace('OPERATION_LITERAL',repr(operation)),timeout=80)
    copies=report.pop('originalCopies')
    destination=PRIVATE/'failed-restore-361-originals'
    destination.mkdir(exist_ok=True)
    import base64
    for name,data in copies.items():
        path=destination/name
        assert path.resolve().is_relative_to(destination.resolve())
        raw=base64.b64decode(data)
        path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists():assert path.read_bytes()==raw
        else:path.write_bytes(raw)
    report['privateOriginalCopiesVerified']=len(copies)
    (TASK/'database-state-failure-diagnosis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='evidencePins'}))
