"""Read every audited binlog segment through the actual isolated native tool."""
import json
from common import TASK,PRIVATE,remote,write

SCRIPT=r'''
import datetime,fcntl,hashlib,json,os,pathlib,subprocess,sys,time
from types import SimpleNamespace
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
def need(value,code):
 if not value:raise ValueError(code)
def pin(p):
 p=pathlib.Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):need(pin(p['path'])==p,'INPUT_PIN_CHANGED');return json.loads(pathlib.Path(p['path']).read_bytes())
def run(args,secret=None):
 p=subprocess.run(args,input=secret,capture_output=True,timeout=30);need(p.returncode==0 and not p.stderr,'READONLY_COMMAND_FAILED');return p.stdout
def snapshot():
 ids=run(['docker','ps','-aq','--no-trunc']).decode().split();rows=json.loads(run(['docker','inspect',*ids]))
 return {r['Id']:dict(state={k:r['State'][k] for k in ('Running','Paused','Restarting','Pid','StartedAt','FinishedAt')},definition=hashlib.sha256(json.dumps(dict({k:r[k] for k in ('Config','HostConfig','Path','Args','Image')},Mounts=sorted(r['Mounts'],key=lambda m:m['Destination'])),sort_keys=True,separators=(',',':')).encode()).hexdigest()) for r in rows}
need(not pathlib.Path('/var/lib/spug-restore-resources/active.json').exists(),'ACTIVE_RESERVATION')
lock=os.open('/var/lib/docker/intruoyi-data/prod-spug-backup-20261019/source-locks/source.lock',os.O_RDWR|os.O_NOFOLLOW);fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
owner=read(INSTALLATION['ownerConfigurationPin']);source=json.loads(pathlib.Path(owner['sources'][SOURCE]['configurationPath']).read_bytes())['source']
tool=read(PROVISIONED['descriptorPin']);secretpin=source['passwordPin'];secret=pathlib.Path(secretpin['path']).read_bytes();need(pin(secretpin['path'])==secretpin,'MYSQL_SECRET_CHANGED')
engine=pathlib.Path(INSTALLATION['engine']);sys.path[:0]=[str(engine/'formal'),str(engine/'common')]
from minimal_capture_support import MinimalSeries
from formal_capture_budget import drain_owned_process
series=SimpleNamespace(binlog_tool=tool,mysql_source=source['mysqlContainerId'],guard=lambda:None)
def verify():
 need(MinimalSeries.binlog_container(series,None)==PROVISIONED['containerId'],'WRONG_EXPORTER')
 r=json.loads(run(['docker','inspect',tool['containerId']]))[0];h=r['HostConfig']
 need(r['Config']['User']==PROVISIONED['user']=='999:999' and h['Tmpfs']==PROVISIONED['tmpfs'] and h['CapDrop']==['ALL'] and not h.get('CapAdd') and h['ReadonlyRootfs'] and h['Memory']==h['MemorySwap']==PROVISIONED['memoryBytes'] and h['PidsLimit']==PROVISIONED['pidsLimit'],'EXPORTER_TEMPORARY_CONTRACT_CHANGED')
 need(not h.get('Binds') and all(m['Type']=='tmpfs' for m in r['Mounts']),'SOURCE_DATA_VOLUME_FORBIDDEN')
 shell='IFS= read -r MYSQL_PWD; export MYSQL_PWD; exec "$@"'
 flags=run(['docker','exec','-i',source['mysqlContainerId'],'sh','-ec',shell,'readonly-export-regression','mysql','--no-defaults','--batch','--skip-column-names','-e','SELECT @@server_uuid,@@GLOBAL.event_scheduler,@@GLOBAL.read_only,@@GLOBAL.super_read_only;'],secret.rstrip(b'\n')+b'\n').decode().strip().split('\t')
 need(flags==[source['databaseUuid'],'ON','0','0'],'SOURCE_GLOBAL_STATE_CHANGED')
verify();before=snapshot();started=time.monotonic();total=0;segments=[]
class Sink:
 def __init__(self):self.bytes=0;self.sha=hashlib.sha256()
 def write(self,raw):
  self.bytes+=len(raw);need(self.bytes<=4*1024**3,'EXPORT_SEGMENT_BYTES_EXCEEDED');self.sha.update(raw)
shell='test -z "${MYSQL_TEST_LOGIN_FILE:-}"; test -n "${HOME:-}"; test ! -e "$HOME/.mylogin.cnf"; test ! -L "$HOME/.mylogin.cnf"; IFS= read -r MYSQL_PWD; export MYSQL_PWD; exec timeout --signal=TERM --kill-after=5s 180s mysqlbinlog "$@"'
for segment in AUDIT['segments']:
 need(time.monotonic()-started<600,'FULL_EXPORT_DIAGNOSTIC_DEADLINE')
 args=['docker','exec','-i',tool['containerId'],'sh','-ec',shell,'capture-binlog-full-readonly-regression','--no-defaults','--read-from-remote-server',*MinimalSeries.binlog_connection(series),'--user=root','--verify-binlog-checksum','--disable-log-bin','--start-position='+str(segment['startPosition']),'--stop-position='+str(segment['stopPosition']),segment['file']]
 sink=Sink();p=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE);begin=time.monotonic()
 result=drain_owned_process(p,secret.rstrip(b'\n')+b'\n',sink,guard=lambda:None,deadline=min(started+600,begin+185),stderr_limit=0)
 need(result['stdoutBytes']==sink.bytes and sink.bytes>0 and result['returncode']==0 and result['stderrBytes']==0,'FULL_NATIVE_EXPORT_REQUIRED')
 total+=sink.bytes;need(total<=32*1024**3,'FULL_NATIVE_EXPORT_OUTPUT_LIMIT')
 segments.append(dict(segment=segment,**result,stdoutSha256=sink.sha.hexdigest(),elapsedSeconds=round(time.monotonic()-begin,3)))
need(segments[0]['stdoutBytes']==PROVISIONED['nativeExport']['stdoutBytes'] and segments[0]['stdoutSha256']==PROVISIONED['nativeExport']['sha256'],'FIRST_SEGMENT_REPRODUCTION_CHANGED')
verify();need(snapshot()==before,'ORIGINAL_CONTAINER_STATE_CHANGED')
os.close(lock)
print(json.dumps(dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),sourceConfigRef=SOURCE,containerId=tool['containerId'],descriptorPin=PROVISIONED['descriptorPin'],parentChainRef=AUDIT['parentChainRef'],parentPointPin=AUDIT['parentPointPin'],start=AUDIT['start'],end=AUDIT['end'],binlogBytes=AUDIT['binlogBytes'],segments=segments,totalSqlBytes=total,totalStderrBytes=sum(s['stderrBytes'] for s in segments),actualNativeAllSegmentsExported=True,allActualExitCodesZero=True,firstSegmentReproductionExact=True,originalContainersPreserved=True,originalContainerCount=len(before),sourceGlobalStatePreserved=True,readOnlyBusinessData=True,backupPerformed=False,restorePerformed=False,elapsedSeconds=round(time.monotonic()-started,3))))
'''

if __name__=='__main__':
 output=TASK/'binlog-tmpfs-full-native-export.json';assert not output.exists(),'FULL_EXPORT_ALREADY_RECORDED'
 audit=json.loads((TASK/'binlog-scope-tmpfs-candidate.json').read_text(encoding='utf-8'))
 provisioned=json.loads((TASK/'binlog-tmpfs-tool-provisioned.json').read_text(encoding='utf-8'))
 installation=json.loads((TASK/'source-control-parent-installation.json').read_text(encoding='utf-8'))
 assert audit['status']==provisioned['status']=='PASS' and not audit['diagnostics']
 variables=dict(SOURCE='intruoyi-57-safe-20261024-v1',INSTALLATION=installation,PROVISIONED=provisioned,AUDIT=audit)
 script='\n'.join(k+'='+repr(v) for k,v in variables.items())+'\n'+SCRIPT;compile(script,'<real-all-segment-export>','exec')
 value=remote('172.30.30.57',script,650);write(PRIVATE/'binlog-tmpfs-full-native-export.private.json',value);write(output,value);print(json.dumps({k:v for k,v in value.items() if k!='segments'}|dict(segmentCount=len(value['segments']))))
