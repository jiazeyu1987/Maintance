"""Require failed-original retention and a fresh strict audit before retry two."""
import datetime,hashlib,json
from common import PRIVATE,TASK,SOURCE,remote,write,now

SCRIPT=r'''
import hashlib,json,pathlib,subprocess
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
assert not pathlib.Path('/var/lib/spug-restore-resources/active.json').exists(),'ACTIVE_RESERVATION'
for reference in FAILED_PINS:
 raw=pathlib.Path(reference['path']).read_bytes();assert len(raw)==reference['bytes'] and hashlib.sha256(raw).hexdigest()==reference['sha256'],'FAILED_ORIGINAL_CHANGED'
config=json.loads((root/'configuration/capture.json').read_bytes());source=config['source']
pin=source['passwordPin'];secret=pathlib.Path(pin['path']).read_bytes();assert len(secret)==pin['bytes'] and hashlib.sha256(secret).hexdigest()==pin['sha256']
mysql=source['mysqlContainerId']
def run(args):
 p=subprocess.run(args,input=secret.rstrip(b'\n')+b'\n',capture_output=True,timeout=30);assert p.returncode==0,'READONLY_TRANSPORT_PREFLIGHT_FAILED';return p.stdout
shell='IFS= read -r MYSQL_PWD; export MYSQL_PWD; exec "$@"'
flags=run(['docker','exec','-i',mysql,'sh','-ec',shell,'retry-readonly','mysql','--no-defaults','--batch','--skip-column-names','-e','SELECT @@server_uuid,@@GLOBAL.event_scheduler,@@GLOBAL.read_only,@@GLOBAL.super_read_only;']).decode().strip().split('\t')
assert flags==[source['databaseUuid'],'ON','0','0'],'SOURCE_FLAGS_DRIFT'
toolref=next(r['reference'] for r in source['materialPins'] if r['purpose']=='mysqlbinlog-exporter');tool=json.loads(pathlib.Path(toolref['path']).read_bytes())
transport='test -z "${MYSQL_TEST_LOGIN_FILE:-}"; test -n "${HOME:-}"; test ! -e "$HOME/.mylogin.cnf"; test ! -L "$HOME/.mylogin.cnf"; IFS= read -r MYSQL_PWD; export MYSQL_PWD; exec mysqlbinlog "$@"'
raw=run(['docker','exec','-i',tool['containerId'],'sh','-ec',transport,'capture-binlog','--no-defaults','--read-from-remote-server','--protocol=SOCKET','--socket=/proc/1/root/var/run/mysqld/mysqld.sock','--user=root','--disable-log-bin','--database='+source['database'],'--start-position='+str(POSITION['position']),'--stop-position='+str(POSITION['position']),POSITION['file']])
assert raw and b'ERROR' not in raw,'BINLOG_READONLY_PROBE_FAILED'
bindings=[]
for p in (root/'registry/points').glob('*.json'):
 ref=json.loads(p.read_bytes());value=json.loads(pathlib.Path(ref['path']).read_bytes());bindings.append(value['reference'])
assert 'smallapp-a690233d967d4965bf5f861dc1126961' not in bindings,'FAILED_POINT_PUBLISHED'
print(json.dumps(dict(status='PASS',failedPointNotPublished=True,failedOriginalPinsVerified=len(FAILED_PINS),databaseUuid=flags[0],eventScheduler=flags[1],readOnly=flags[2],superReadOnly=flags[3],actualNativeBinlogTransportVerified=True,probeOutputBytes=len(raw),probeOutputSha256=hashlib.sha256(raw).hexdigest(),businessDataChanged=False)))
'''
if __name__=='__main__':
 load=lambda name:json.loads((TASK/name).read_text(encoding='utf-8'))
 audit=load('binlog-scope-installed-retry-2.json');tool=load('registered-binlog-tool-restored.json');terminal=load('incremental-terminal-record.json');baseline=load('after-tool-start-57.json')
 assert audit['status']==tool['status']=='PASS' and not audit['diagnostics']
 assert terminal['result']['state']=='FAILED' and terminal['result']['errorCode']=='MINIMAL_BINLOG_TOOL_CHANGED'
 assert (datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(audit['finishedAt'])).total_seconds()<900,'AUDIT_STALE'
 assert not (TASK/'incremental-2-ui-submission.json').exists()
 assert baseline['http']['backend']['status']=='UP' and baseline['http']['frontend']['httpStatus']==200 and not baseline['activeReservation']
 value=remote('172.30.30.57','FAILED_PINS='+repr(tool['failedOriginalPins'])+'\nPOSITION='+repr(audit['start'])+'\n'+SCRIPT,80)
 value.update(observedAt=now(),sourceConfigRef=SOURCE,parentChainRef=audit['parentChainRef'],parentPointPin=audit['parentPointPin'],installedModulePin=audit['installedModulePin'],auditedStart=audit['start'],auditedEnd=audit['end'],binlogBytes=audit['binlogBytes'],sourceCommit='6319024c003ead602d59e7697673fa3c39807863',originalAttempt='smallapp-a690233d967d4965bf5f861dc1126961',originalAttemptActualExitCode=1)
 write(TASK/'incremental-2-preflight.json',value);print(json.dumps(value))
