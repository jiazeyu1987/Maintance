"""Independently check source global state, tool and retained failure originals."""
import json
from common import PRIVATE,TASK,active_source_installation,remote,write,now

SCRIPT=r'''
import hashlib,json,os,pathlib,stat,subprocess,sys,time
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
capture_raw=pathlib.Path(CAPTURE_PIN['path']).read_bytes()
assert len(capture_raw)==CAPTURE_PIN['bytes'] and hashlib.sha256(capture_raw).hexdigest()==CAPTURE_PIN['sha256'],'ACTIVE_CAPTURE_CHANGED'
configuration=json.loads(capture_raw);source=configuration['source']
reference=source['passwordPin'];secret=pathlib.Path(reference['path']).read_bytes();assert len(secret)==reference['bytes'] and hashlib.sha256(secret).hexdigest()==reference['sha256']
shell='IFS= read -r MYSQL_PWD; export MYSQL_PWD; exec "$@"'
raw=subprocess.check_output(['docker','exec','-i',source['mysqlContainerId'],'sh','-ec',shell,'source-restoration-readonly','mysql','--no-defaults','--batch','--skip-column-names','-e','SELECT @@server_uuid,@@version,@@GLOBAL.event_scheduler,@@GLOBAL.read_only,@@GLOBAL.super_read_only;'],input=secret.rstrip(b'\n')+b'\n',timeout=15)
flags=raw.decode().strip().split('\t');assert flags==['0fa6c22b-5a90-11f1-ade1-0242ac150002','8.0.39','ON','0','0'],'SOURCE_FLAGS_NOT_RESTORED'
engine=pathlib.Path(ENGINE);sys.path[:0]=[str(engine/'common'),str(engine/'formal'),'/var/lib/docker/intruoyi-data/prod-spug-backup-20261019/runtime/lib/python3.12/site-packages']
from minimal_capture_support import MinimalSeries
from types import SimpleNamespace
toolpin=next(row['reference'] for row in source['materialPins'] if row['purpose']=='mysqlbinlog-exporter')
assert toolpin==EXPORTER['descriptorPin'],'REGISTERED_EXPORTER_CHANGED'
toolraw=pathlib.Path(toolpin['path']).read_bytes()
assert len(toolraw)==toolpin['bytes'] and hashlib.sha256(toolraw).hexdigest()==toolpin['sha256'],'REGISTERED_EXPORTER_DESCRIPTOR_CHANGED'
tool=json.loads(toolraw)
assert tool['containerId']==EXPORTER['containerId'],'REGISTERED_EXPORTER_ID_CHANGED'
assert MinimalSeries.binlog_container(SimpleNamespace(binlog_tool=tool,mysql_source=source['mysqlContainerId'],guard=lambda:None),None)==tool['containerId']
row=json.loads(subprocess.check_output(['docker','inspect',tool['containerId']],timeout=15))[0];host=row['HostConfig']
assert row['Config']['User']=='999:999' and host['Tmpfs']==EXPORTER['tmpfs'] and host['CapDrop']==['ALL'] and not host.get('CapAdd'),'REGISTERED_EXPORTER_TEMPORARY_CONTRACT_CHANGED'
assert host['Memory']==host['MemorySwap']==EXPORTER['memoryBytes'] and host['PidsLimit']==EXPORTER['pidsLimit'],'REGISTERED_EXPORTER_RESOURCE_CONTRACT_CHANGED'
assert not host.get('Binds') and all(m['Type']=='tmpfs' for m in row['Mounts']),'REGISTERED_EXPORTER_SOURCE_DATA_VOLUME_FORBIDDEN'
deadline=time.monotonic()+90
def identity(info):return (info.st_dev,info.st_ino,info.st_mode,info.st_nlink,info.st_size,info.st_mtime_ns,info.st_ctime_ns)
for pin in FAILED_PINS:
 path=pathlib.Path(pin['path']);before=path.lstat();sha=hashlib.sha256();size=0
 assert path.resolve()==path and stat.S_ISREG(before.st_mode) and before.st_nlink==1,'FAILED_ORIGINAL_PATH_CHANGED'
 with os.fdopen(os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK),'rb') as stream:
  assert identity(os.fstat(stream.fileno()))==identity(before),'FAILED_ORIGINAL_CHANGED'
  while True:
   assert time.monotonic()<deadline,'FAILED_ORIGINAL_READ_DEADLINE'
   raw=stream.read(1024*1024)
   if not raw:break
   sha.update(raw);size+=len(raw)
  assert identity(os.fstat(stream.fileno()))==identity(before),'FAILED_ORIGINAL_CHANGED'
 assert identity(path.lstat())==identity(before) and size==pin['bytes'] and sha.hexdigest()==pin['sha256'],'FAILED_ORIGINAL_CHANGED'
assert not pathlib.Path('/var/lib/spug-restore-resources/active.json').exists(),'SOURCE_RESOURCE_RESERVATION_REMAINS'
print(json.dumps(dict(status='PASS',databaseUuid=flags[0],version=flags[1],eventScheduler=flags[2],readOnly=flags[3],superReadOnly=flags[4],originalGlobalStateRestored=True,strictBinlogToolStillVerified=True,registeredExporterTemporaryContractVerified=True,activeCaptureConfigurationPin=CAPTURE_PIN,exporterDescriptorPin=toolpin,failedOriginalFilesPreserved=len(FAILED_PINS))))
'''
if __name__=='__main__':
 point=json.loads((TASK/'new-incremental-point-verified.json').read_text(encoding='utf-8'));pins=json.loads((TASK/'registered-binlog-tool-restored.json').read_text(encoding='utf-8'))['failedOriginalPins']
 for history in ('365','366'):pins+=json.loads((PRIVATE/('failed-'+history+'-all-pins.private.json')).read_text(encoding='utf-8'))['pins']
 assert len(pins)==10044
 installed=active_source_installation();exporter=json.loads((TASK/'binlog-tmpfs-tool-provisioned.json').read_text(encoding='utf-8'))
 variables=dict(ENGINE=installed['engine'],FAILED_PINS=pins,CAPTURE_PIN=installed['captureConfigurationPin'],EXPORTER=exporter)
 report=remote('172.30.30.57','\n'.join(k+'='+repr(v) for k,v in variables.items())+'\n'+SCRIPT,120);report.update(observedAt=now(),backupOperationId=point['operationId'])
 write(TASK/'source-global-state-restored.json',report);print(json.dumps(report))
