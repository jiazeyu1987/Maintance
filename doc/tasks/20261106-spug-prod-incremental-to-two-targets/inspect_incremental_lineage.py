"""Inspect actual published capture endpoints and current retained binlogs."""
import json
from common import PRIVATE,TASK,remote,write

SCRIPT=r'''
import datetime,hashlib,json,pathlib,subprocess
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
def read(pin):
 raw=pathlib.Path(pin['path']).read_bytes()
 assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'],'CHAIN_METADATA_PIN_CHANGED'
 return json.loads(raw)
capture=json.loads((root/'configuration/capture.json').read_bytes())
source=capture['source'];password=pathlib.Path(source['passwordPin']['path']).read_text().strip()
assert hashlib.sha256(pathlib.Path(source['passwordPin']['path']).read_bytes()).hexdigest()==source['passwordPin']['sha256']
sql='SELECT @@server_uuid,@@version,@@GLOBAL.log_bin,@@GLOBAL.binlog_format,@@GLOBAL.gtid_mode,@@GLOBAL.event_scheduler,@@GLOBAL.read_only,@@GLOBAL.super_read_only; SHOW MASTER STATUS; SHOW BINARY LOGS;'
shell='IFS= read -r MYSQL_PWD; export MYSQL_PWD; exec "$@"'
p=subprocess.run(['docker','exec','-i',source['mysqlContainerId'],'sh','-ec',shell,'readonly-lineage','mysql','--no-defaults','--batch','--skip-column-names','-e',sql],input=(password+'\n').encode(),capture_output=True,timeout=30)
assert p.returncode==0 and not p.stderr,'MYSQL_LINEAGE_QUERY_FAILED'
out=dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),mysqlRows=p.stdout.decode().splitlines(),points=[],sourceLockPath=capture['sourceLockPath'])
for path in (root/'registry/points').glob('*.json'):
 binding=read(json.loads(path.read_bytes()))
 result=read(binding['resultPin']);data=result['data'];point=read(data['pointPin']);manifest=read(data['manifestPin'])
 candidates=[ref for ref in point['payloadRefs'] if ref['path'].endswith('/capture-content-point.json')]
 if not candidates:
  out['points'].append(dict(reference=binding['reference'],pointType=point['pointType'],capturePointCandidates=[r['path'] for r in point['payloadRefs'] if 'point' in r['path'] or 'catalog' in r['path']]))
  continue
 assert len(candidates)==1,'CAPTURE_POINT_AMBIGUOUS'
 capturepoint=read(candidates[0])
 out['points'].append(dict(reference=binding['reference'],pointType=point['pointType'],backupId=point['backupId'],generationId=point['generationId'],finishedAt=result['finishedAt'],state=result['state'],actualExitCode=result['actualExitCode'],pointPin=data['pointPin'],manifestPin=data['manifestPin'],capturePointPin=candidates[0],databaseEnd=capturepoint['databaseEnd'],databaseDelta=capturepoint['databaseDelta'],parentPointPins=point['parentPointPins'],commonRecoveryPoint=point['commonRecoveryPoint'],payloadFiles=len(point['payloadRefs']),payloadBytes=sum(r['bytes'] for r in point['payloadRefs'])))
control=json.loads((root/'configuration/control-postboot-20261105.json').read_bytes())
out['sourceControlBudget']={k:control[k] for k in ('deadlineMilliseconds','environment','workingDirectory')}
out['sourceProcessLimits']=subprocess.check_output(['systemctl','show','spug-intruoyi-source-57-20261105.service','-p','MainPID','-p','LimitNOFILE','-p','ActiveState']).decode()
out['sourceEngineBinlogSource']=[]
for p in [root/'engine/formal/formal_capture_incremental.py',*pathlib.Path('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3/engine-mainv2-9dce318/common').glob('*mysql*.py'),*pathlib.Path('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3/engine-mainv2-9dce318/common').glob('*import*.py')]:
 lines=p.read_text().splitlines()
 out['sourceEngineBinlogSource'].append(dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),matches=[dict(line=i+1,text=line) for i,line in enumerate(lines) if any(v in line for v in ('sql_log_bin','disable-log-bin','DROP DATABASE','CREATE DATABASE','mysqlbinlog','database_log_mode'))]))
print(json.dumps(out))
'''

if __name__=='__main__':
    value=remote('172.30.30.57',SCRIPT,180)
    write(PRIVATE/'incremental-lineage.private.json',value)
    report={k:v for k,v in value.items() if k!='sourceControlBudget'}
    report['sourceControlDeadlineMilliseconds']=value['sourceControlBudget']['deadlineMilliseconds']
    write(TASK/'incremental-lineage.json',report)
    print(json.dumps(report,ensure_ascii=False))
