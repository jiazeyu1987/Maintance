"""Provision one immutable exporter with bounded private temporary filesystems.

Keeps the old registered tool and every business container. Does not activate
the new descriptor or perform a backup/restore. A real nonempty export must
succeed before the descriptor can be registered in a new control generation.
"""
import argparse,hashlib,json
from common import TASK,PRIVATE,remote,write

SCRIPT=r'''
import datetime,fcntl,hashlib,json,os,pathlib,subprocess,sys,time
from types import SimpleNamespace
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
name='spug-intruoyi57-binlog-tmpfs-20261107-v'+str(GENERATION)
descriptor_path=root/('configuration/mysqlbinlog-tmpfs-20261107-v'+str(GENERATION)+'.json')
assert not descriptor_path.exists(),'EXPORTER_DESCRIPTOR_ALREADY_EXISTS'
def need(value,code):
 if not value:raise ValueError(code)
def run(args,seconds=30,input=None):
 p=subprocess.run(args,input=input,capture_output=True,timeout=seconds)
 need(p.returncode==0 and not p.stderr,'EXPORTER_INSTALL_COMMAND_FAILED');return p.stdout
def docker(args):return run(['docker',*args])
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':')).encode()
def pin(path):
 path=pathlib.Path(path);raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(p):need(pin(p['path'])==p,'ORIGINAL_PIN_CHANGED');return json.loads(pathlib.Path(p['path']).read_bytes())
def snapshot():
 rows=json.loads(docker(['inspect',*docker(['ps','-aq','--no-trunc']).decode().split()]))
 return {r['Id']:dict(image=r['Image'],state={k:r['State'][k] for k in ('Running','Paused','Restarting','Pid','StartedAt','FinishedAt')},definitionSha256=hashlib.sha256(canonical(dict({k:r[k] for k in ('Path','Args','HostConfig','Config')},Mounts=sorted(r['Mounts'],key=lambda m:m['Destination'])))).hexdigest()) for r in rows}
def mounts():
 paths=['/mnt/nas','/var/lib/docker/intruoyi-data/prod57-spug-rehearsal-20261021/nas']
 return sorted(' '.join(l.split()[1:]) for l in pathlib.Path('/proc/self/mountinfo').read_text().splitlines() if any(p==l.split()[4] or p.startswith(l.split()[4].rstrip('/')+'/') or l.split()[4].startswith(p.rstrip('/')+'/') for p in paths))
need(not pathlib.Path('/var/lib/spug-restore-resources/active.json').exists(),'ACTIVE_RESERVATION')
for process in pathlib.Path('/proc').iterdir():
 if not process.name.isdecimal():continue
 try:command=(process/'cmdline').read_bytes()
 except (FileNotFoundError,ProcessLookupError):continue
 if str(root).encode() in command:need(b'control_entry.py' in command,'ACTIVE_SOURCE_WORKER')
lock=os.open('/var/lib/docker/intruoyi-data/prod-spug-backup-20261019/source-locks/source.lock',os.O_RDWR|os.O_NOFOLLOW);fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
read(INSTALLATION['controlConfigurationPin']);owner=read(INSTALLATION['ownerConfigurationPin'])
capture_path=pathlib.Path(owner['sources'][SOURCE]['configurationPath']);source=json.loads(capture_path.read_bytes())['source']
secretpin=source['passwordPin'];secret=pathlib.Path(secretpin['path']).read_bytes();need(pin(secretpin['path'])==secretpin,'MYSQL_SECRET_CHANGED')
def source_flags():
 shell='IFS= read -r MYSQL_PWD; export MYSQL_PWD; exec "$@"'
 sql='SELECT @@server_uuid,@@GLOBAL.event_scheduler,@@GLOBAL.read_only,@@GLOBAL.super_read_only;'
 fields=run(['docker','exec','-i',source['mysqlContainerId'],'sh','-ec',shell,'exporter-install-readonly','mysql','--no-defaults','--batch','--skip-column-names','-e',sql],input=secret.rstrip(b'\n')+b'\n').decode().strip().split('\t')
 need(fields==[source['databaseUuid'],'ON','0','0'],'SOURCE_GLOBAL_STATE_DRIFT')
source_flags()
toolpin=next(r['reference'] for r in source['materialPins'] if r['purpose']=='mysqlbinlog-exporter');old=read(toolpin)
engine=pathlib.Path(INSTALLATION['engine']);version=json.loads((engine/'package.json').read_bytes())
need(len(version['files'])==127 and all(pin(engine/n)['sha256']==sha for n,sha in version['files'].items()),'SOURCE_ENGINE_CHANGED')
sys.path[:0]=[str(engine/'formal'),str(engine/'common')]
from minimal_capture_support import MinimalSeries
from formal_capture_budget import drain_owned_process
MinimalSeries.binlog_container(SimpleNamespace(binlog_tool=old,mysql_source=source['mysqlContainerId'],guard=lambda:None),None)
oldrow=json.loads(docker(['inspect',old['containerId']]))[0]
need(oldrow['Config']['User']=='999:999' and oldrow['HostConfig']['CapDrop']==['ALL'] and not oldrow['HostConfig'].get('CapAdd'),'ORIGINAL_EXPORTER_USER_CONTRACT_CHANGED')
memory=dict(l.split(':',1) for l in pathlib.Path('/proc/meminfo').read_text().splitlines());need(int(memory['MemAvailable'].strip().split()[0])*1024>=4*1024**3,'EXPORTER_MEMORY_CAPACITY_REQUIRED')
before=snapshot();before_mounts=mounts();fstab=pin('/etc/fstab')
need(subprocess.run(['docker','inspect',name],capture_output=True).returncode!=0,'EXPORTER_NAME_ALREADY_EXISTS')
temporary='/tmp:rw,noexec,nosuid,nodev,size=1073741824,mode=1777'
unused_data='/var/lib/mysql:rw,noexec,nosuid,nodev,size=1048576,mode=0700'
created=docker(['create','--name',name,'--label','spug.component=mysqlbinlog-exporter','--label','spug.source='+source['mysqlContainerId'],'--read-only','--cap-drop=ALL','--user',oldrow['Config']['User'],'--security-opt=no-new-privileges:true','--network','container:'+source['mysqlContainerId'],'--pid','container:'+source['mysqlContainerId'],'--ipc','private','--pids-limit','64','--memory','2147483648','--memory-swap','2147483648','--restart','unless-stopped','--tmpfs',temporary,'--tmpfs',unused_data,'--entrypoint','sleep',old['imageId'],'infinity']).decode().strip()
need(len(created)==64,'EXPORTER_CREATE_ID_INVALID');docker(['start',created])
def verify():
 row=json.loads(docker(['inspect',created]))[0];host=row['HostConfig']
 need(row['Id']==created and row['Image']==old['imageId'] and row['State']['Running'] and not row['State']['Paused'] and not row['State']['Restarting'],'NEW_EXPORTER_NOT_RUNNING')
 need(row['Path']=='sleep' and row['Args']==['infinity'] and host['ReadonlyRootfs'] and host['NetworkMode']==host['PidMode']=='container:'+source['mysqlContainerId'],'NEW_EXPORTER_BINDING_INVALID')
 need(host['Tmpfs']=={'/tmp':temporary.split(':',1)[1],'/var/lib/mysql':unused_data.split(':',1)[1]} and not host.get('Binds') and all(m['Type']=='tmpfs' for m in row['Mounts']),'NEW_EXPORTER_TEMPORARY_MOUNTS_INVALID')
 need(host['Memory']==host['MemorySwap']==2147483648 and host['PidsLimit']==64 and host['CapDrop']==['ALL'] and not host.get('CapAdd') and host['RestartPolicy']=={'Name':'unless-stopped','MaximumRetryCount':0},'NEW_EXPORTER_RESOURCE_CONTRACT_CHANGED')
 need(row['Config']['User']==oldrow['Config']['User'],'NEW_EXPORTER_USER_CHANGED')
 need(docker(['exec',created,'sha256sum',old['executable']]).decode().split()==[old['sha256'],old['executable']],'NEW_EXPORTER_BINARY_CHANGED')
 return row
row=verify()
probe='set -eu; test ! -e /tmp/spug-exporter-probe; umask 077; p=$(mktemp /tmp/spug-exporter-probe.XXXXXX); trap \'rm -f -- "$p"\' EXIT; dd if=/dev/zero of="$p" bs=1048576 count=1 status=none; test "$(wc -c < "$p")" = 1048576; stat -f -c %T /tmp; stat -c %a /tmp; test ! -w /etc'
observed=docker(['exec',created,'sh','-ec',probe]).decode().splitlines();need(observed==['tmpfs','1777'],'NEW_EXPORTER_TEMPORARY_PROBE_FAILED')
shell='test -z "${MYSQL_TEST_LOGIN_FILE:-}"; test -n "${HOME:-}"; test ! -e "$HOME/.mylogin.cnf"; test ! -L "$HOME/.mylogin.cnf"; IFS= read -r MYSQL_PWD; export MYSQL_PWD; exec timeout --signal=TERM --kill-after=5s 180s mysqlbinlog "$@"'
args=['docker','exec','-i',created,'sh','-ec',shell,'capture-binlog-readonly-preflight','--no-defaults','--read-from-remote-server',*MinimalSeries.binlog_connection(None),'--user=root','--verify-binlog-checksum','--disable-log-bin','--start-position='+str(SEGMENT['startPosition']),'--stop-position='+str(SEGMENT['stopPosition']),SEGMENT['file']]
class Sink:
 def __init__(self):self.bytes=0;self.sha=hashlib.sha256()
 def write(self,raw):
  self.bytes+=len(raw);need(self.bytes<=4*1024**3,'NATIVE_EXPORT_PROBE_OUTPUT_LIMIT');self.sha.update(raw)
sink=Sink();started=time.monotonic();process=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
native=drain_owned_process(process,secret.rstrip(b'\n')+b'\n',sink,guard=lambda:None,deadline=time.monotonic()+185,stderr_limit=0)
need(native['stdoutBytes']==sink.bytes and sink.bytes>0 and native['returncode']==0 and native['stderrBytes']==0,'NATIVE_NONEMPTY_EXPORT_REQUIRED')
verify();source_flags();after=snapshot();need(after.pop(created,None) is not None and after==before,'ORIGINAL_CONTAINER_STATE_CHANGED')
need(mounts()==before_mounts and pin('/etc/fstab')==fstab,'PROTECTED_MOUNTS_CHANGED')
descriptor=dict(old,containerId=created);raw=canonical(descriptor)
fd=os.open(descriptor_path,os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_WRONLY,0o600)
with os.fdopen(fd,'wb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
need(descriptor_path.read_bytes()==raw,'NEW_EXPORTER_DESCRIPTOR_READBACK_FAILED')
MinimalSeries.binlog_container(SimpleNamespace(binlog_tool=descriptor,mysql_source=source['mysqlContainerId'],guard=lambda:None),None)
report=dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),sourceConfigRef=SOURCE,containerId=created,containerName=name,imageId=old['imageId'],executable=old['executable'],executableSha256=old['sha256'],descriptorPin=pin(descriptor_path),oldDescriptorPin=toolpin,oldContainerId=old['containerId'],sourceMysqlContainerId=source['mysqlContainerId'],readOnlyRootfs=True,user=row['Config']['User'],tmpfs=row['HostConfig']['Tmpfs'],capabilities=row['HostConfig'].get('CapAdd') or [],memoryBytes=2147483648,pidsLimit=64,sourceNetworkAndPidNamespaceVerified=True,noSourceDataVolumes=True,temporaryWriteProbeBytes=1048576,temporaryFilesystem='tmpfs',temporaryMode='1777',actualFirstSegment=SEGMENT,nativeExport=dict(**native,sha256=sink.sha.hexdigest(),elapsedSeconds=round(time.monotonic()-started,3)),originalContainerCount=len(before),allOriginalDefinitionsAndRuntimePreserved=True,fstabAndProtectedMountsPreserved=True,sourceOriginalGlobalFlagsPreserved=True,registered=False,backupPerformed=False,restorePerformed=False)
os.close(lock);print(json.dumps(report))
'''

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--prepare-only',action='store_true');parser.add_argument('--generation',type=int,choices=[3],default=3);args=parser.parse_args()
 destination=TASK/'binlog-tmpfs-tool-provisioned.json';assert not destination.exists(),'TOOL_PROVISIONING_ALREADY_RECORDED'
 red=json.loads((TASK/'incremental-366-export-stderr-bdd-red.json').read_text(encoding='utf-8'))
 assert red['readOnlyTemporaryFilesystemError'] and red['actualExitCode']!=0 and red['stderrBytes']>0
 installation=json.loads((TASK/'source-control-parent-installation.json').read_text(encoding='utf-8'))
 segment=json.loads((TASK/'binlog-scope-parent-installed.json').read_text(encoding='utf-8'))['segments'][0]
 variables=dict(GENERATION=args.generation,SOURCE='intruoyi-57-safe-20261024-v1',INSTALLATION=installation,SEGMENT=segment)
 script='\n'.join(k+'='+repr(v) for k,v in variables.items())+'\n'+SCRIPT
 compile(script,'<binlog-tmpfs-provisioning>','exec')
 if args.prepare_only:
  value=dict(status='PASS',preparedOnly=True,remoteWrites=False,scriptSha256=hashlib.sha256(script.encode()).hexdigest(),sourceEngine=installation['engine'],realRedConfirmed=True)
  destination=TASK/('binlog-tmpfs-provisioning-preflight'+('' if args.generation==1 else '-v'+str(args.generation))+'.json');assert not destination.exists(),'PREFLIGHT_ALREADY_RECORDED'
  write(destination,value);print(json.dumps(value));raise SystemExit(0)
 value=remote('172.30.30.57',script,240);write(PRIVATE/'binlog-tmpfs-tool-provisioned.private.json',value);write(destination,value);print(json.dumps(value))
