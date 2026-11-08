"""Activate immutable exporter configuration while retaining the tested engine."""
import argparse,datetime,hashlib,json
from common import TASK,PRIVATE,remote,write

SCRIPT=r'''
import copy,datetime,fcntl,hashlib,json,os,pathlib,stat,subprocess,sys,time,urllib.error,urllib.request
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1');unit='spug-intruoyi-source-57-20261105.service';generation='binlog-tmpfs-20261107-v3'
def need(v,code):
 if not v:raise ValueError(code)
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def pin(p):
 p=pathlib.Path(p);raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(p):need(pin(p['path'])==p,'INPUT_PIN_CHANGED');return json.loads(pathlib.Path(p['path']).read_bytes())
def run(args,timeout=30,input=None):
 p=subprocess.run(args,input=input,capture_output=True,timeout=timeout);need(p.returncode==0 and not p.stderr,'CONTROL_INSTALL_COMMAND_FAILED');return p.stdout
def write_new(path,raw):
 need(path.is_absolute() and path.parent.resolve()==path.parent,'INSTALL_PATH_INVALID')
 fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_WRONLY,0o600)
 with os.fdopen(fd,'wb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
 need(path.read_bytes()==raw,'INSTALL_READBACK_FAILED');return pin(path)
def snapshot():
 ids=run(['docker','ps','-aq','--no-trunc']).decode().split();rows=json.loads(run(['docker','inspect',*ids]))
 return {r['Id']:dict(state={k:r['State'][k] for k in ('Running','Paused','Restarting','Pid','StartedAt','FinishedAt')},definition=hashlib.sha256(canonical(dict({k:r[k] for k in ('Config','HostConfig','Path','Args','Image')},Mounts=sorted(r['Mounts'],key=lambda m:m['Destination'])))).hexdigest()) for r in rows}
def mounts():
 paths=['/mnt/nas','/var/lib/docker/intruoyi-data/prod57-spug-rehearsal-20261021/nas']
 return sorted(' '.join(l.split()[1:]) for l in pathlib.Path('/proc/self/mountinfo').read_text().splitlines() if any(p==l.split()[4] or p.startswith(l.split()[4].rstrip('/')+'/') or l.split()[4].startswith(p.rstrip('/')+'/') for p in paths))
def verify_failed():
 deadline=time.monotonic()+90
 def identity(i):return (i.st_dev,i.st_ino,i.st_mode,i.st_nlink,i.st_size,i.st_mtime_ns,i.st_ctime_ns)
 for reference in FAILED_PINS:
  path=pathlib.Path(reference['path']);before=path.lstat();sha=hashlib.sha256();size=0
  need(path.resolve()==path and stat.S_ISREG(before.st_mode) and before.st_nlink==1,'FAILED_ORIGINAL_PATH_CHANGED')
  with os.fdopen(os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK),'rb') as stream:
   need(identity(os.fstat(stream.fileno()))==identity(before),'FAILED_ORIGINAL_CHANGED')
   while True:
    need(time.monotonic()<deadline,'FAILED_ORIGINAL_READ_DEADLINE');raw=stream.read(1024*1024)
    if not raw:break
    sha.update(raw);size+=len(raw)
   need(identity(os.fstat(stream.fileno()))==identity(before),'FAILED_ORIGINAL_CHANGED')
  need(identity(path.lstat())==identity(before) and size==reference['bytes'] and sha.hexdigest()==reference['sha256'],'FAILED_ORIGINAL_CHANGED')
need(not pathlib.Path('/var/lib/spug-restore-resources/active.json').exists(),'ACTIVE_RESERVATION')
for process in pathlib.Path('/proc').iterdir():
 if not process.name.isdecimal():continue
 try:command=(process/'cmdline').read_bytes()
 except (FileNotFoundError,ProcessLookupError):continue
 if str(root).encode() in command:need(b'control_entry.py' in command,'ACTIVE_SOURCE_WORKER')
lock=os.open('/var/lib/docker/intruoyi-data/prod-spug-backup-20261019/source-locks/source.lock',os.O_RDWR|os.O_NOFOLLOW);fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
oldcontrol=read(INSTALLATION['controlConfigurationPin']);oldowner=read(INSTALLATION['ownerConfigurationPin'])
need(oldcontrol['sourceConfigurations'][SOURCE]==INSTALLATION['ownerConfigurationPin'],'OLD_OWNER_BINDING_CHANGED')
oldpid=int(run(['systemctl','show',unit,'-p','MainPID']).decode().strip().split('=',1)[1]);need(oldpid==INSTALLATION['pid'],'ACTIVE_SOURCE_PID_CHANGED')
need(INSTALLATION['controlConfigurationPin']['path'].encode() in (pathlib.Path('/proc')/str(oldpid)/'cmdline').read_bytes(),'ACTIVE_SOURCE_CONFIG_CHANGED')
engine=pathlib.Path(INSTALLATION['engine']);version=json.loads((engine/'package.json').read_bytes());need(len(version['files'])==127 and all(pin(engine/n)['sha256']==sha for n,sha in version['files'].items()),'SOURCE_ENGINE_CHANGED')
sys.path[:0]=[str(engine/'formal'),str(engine/'common')]
from minimal_capture_support import MinimalSeries
from types import SimpleNamespace
tool=read(PROVISIONED['descriptorPin']);capturepath=pathlib.Path(oldowner['sources'][SOURCE]['configurationPath']);capturepin=pin(capturepath);capture=json.loads(capturepath.read_bytes());source=capture['source']
need(MinimalSeries.binlog_container(SimpleNamespace(binlog_tool=tool,mysql_source=source['mysqlContainerId'],guard=lambda:None),None)==PROVISIONED['containerId'],'WRONG_EXPORTER')
row=json.loads(run(['docker','inspect',tool['containerId']]))[0];host=row['HostConfig'];need(row['Config']['User']=='999:999' and host['Tmpfs']==PROVISIONED['tmpfs'] and host['CapDrop']==['ALL'] and not host.get('CapAdd') and host['Memory']==host['MemorySwap']==PROVISIONED['memoryBytes'] and host['PidsLimit']==PROVISIONED['pidsLimit'] and not host.get('Binds') and all(m['Type']=='tmpfs' for m in row['Mounts']),'EXPORTER_CONTRACT_CHANGED')
secretpin=source['passwordPin'];need(pin(secretpin['path'])==secretpin,'MYSQL_SECRET_CHANGED');secret=pathlib.Path(secretpin['path']).read_bytes()
def flags():
 sql='SELECT @@server_uuid,@@GLOBAL.event_scheduler,@@GLOBAL.read_only,@@GLOBAL.super_read_only;';shell='IFS= read -r MYSQL_PWD; export MYSQL_PWD; exec "$@"'
 values=run(['docker','exec','-i',source['mysqlContainerId'],'sh','-ec',shell,'control-install-readonly','mysql','--no-defaults','--batch','--skip-column-names','-e',sql],input=secret.rstrip(b'\n')+b'\n').decode().strip().split('\t');need(values==[source['databaseUuid'],'ON','0','0'],'SOURCE_GLOBAL_STATE_CHANGED')
flags();verify_failed();before=snapshot();before_mounts=mounts();fstab=pin('/etc/fstab')
indexes=[i for i,r in enumerate(source['materialPins']) if r['purpose']=='mysqlbinlog-exporter'];need(len(indexes)==1 and source['materialPins'][indexes[0]]['reference']==PROVISIONED['oldDescriptorPin'],'OLD_TOOL_BINDING_CHANGED')
newcapture=copy.deepcopy(capture);newcapture['source']['materialPins'][indexes[0]]['reference']=PROVISIONED['descriptorPin']
newcapturepath=root/'configuration'/('capture-'+generation+'.json');newcapturepin=write_new(newcapturepath,canonical(newcapture))
newowner=copy.deepcopy(oldowner);newowner['sources'][SOURCE]['configurationPath']=str(newcapturepath);ownerpin=write_new(root/'configuration'/('repository-'+generation+'.json'),canonical(newowner))
control=copy.deepcopy(oldcontrol);control['sourceConfigurations'][SOURCE]=ownerpin;controlpath=root/'configuration'/('control-'+generation+'.json');controlpin=write_new(controlpath,canonical(control))
dropin=pathlib.Path('/etc/systemd/system')/(unit+'.d')/('zzzz-'+generation+'.conf')
command=control['pythonPin']['path']+' -B '+str(engine/'control_entry.py')+' serve --config-pin '+"'"+canonical(controlpin).decode()+"'"
text='[Service]\nEnvironment=PYTHONPATH='+control['environment']['PYTHONPATH']+'\nExecStart=\nExecStart='+command+'\n';write_new(dropin,text.encode());dropin.chmod(0o644)
run(['systemctl','daemon-reload']);run(['systemctl','restart',unit]);need(run(['systemctl','is-active',unit]).strip()==b'active','SOURCE_CONTROL_NOT_ACTIVE')
pid=int(run(['systemctl','show',unit,'-p','MainPID']).decode().strip().split('=',1)[1]);need(pid>1 and pid!=oldpid and str(controlpath).encode() in (pathlib.Path('/proc')/str(pid)/'cmdline').read_bytes(),'NEW_CONTROL_NOT_ACTIVE')
limits=(pathlib.Path('/proc')/str(pid)/'limits').read_text();need(any(l.startswith('Max open files') and l.split()[3:5]==['65536','65536'] for l in limits.splitlines()),'LIVE_FD_LIMIT_CHANGED')
headers=json.loads(pathlib.Path(control['authCredentialRef']['path']).read_bytes())['headers'];opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));url='http://127.0.0.1:'+str(control['listenPort'])+'/selections'
for attempt in range(1,22):
 try:
  with opener.open(urllib.request.Request(url,headers=headers),timeout=90) as response:need(response.status==200,'SOURCE_SELECTIONS_HTTP');selections=json.load(response)
  break
 except urllib.error.URLError as error:
  if not isinstance(error.reason,ConnectionRefusedError) or attempt==21:raise
  time.sleep(2)
application=next(a for a in selections['applications'] if a['sourceConfigRef']==SOURCE);need(application['fullReady'] and not application['fullErrorCode'] and not application['historyErrorCode'] and AUDIT['parentChainRef'] in application['parentChainRefs'],'SOURCE_PARENT_NOT_ADMITTED')
flags();verify_failed();need(snapshot()==before,'ORIGINAL_CONTAINER_STATE_CHANGED');need(mounts()==before_mounts and pin('/etc/fstab')==fstab,'PROTECTED_MOUNTS_CHANGED')
read(INSTALLATION['controlConfigurationPin']);read(INSTALLATION['ownerConfigurationPin']);need(pin(capturepath)==capturepin,'OLD_CAPTURE_CONFIGURATION_CHANGED');need(all(pin(engine/n)['sha256']==sha for n,sha in version['files'].items()),'SOURCE_ENGINE_CHANGED')
out=dict(INSTALLATION,status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),oldControlPin=INSTALLATION['controlConfigurationPin'],controlConfigurationPin=controlpin,ownerConfigurationPin=ownerpin,captureConfigurationPin=newcapturepin,dropinPin=pin(dropin),previousPid=oldpid,pid=pid,previousGeneration=INSTALLATION['engine'],failedOriginalFilesPreserved=len(FAILED_PINS),originalContainerCount=len(before),allOriginalContainersUnchanged=True,fstabAndProtectedMountsUnchanged=True,sourceSelectionsHttp=200,sourceSelections=selections,sourceOriginalGlobalFlagsPreserved=True,engineProgramFilesChanged=False,exporterDescriptorPin=PROVISIONED['descriptorPin'],exporterContainerId=PROVISIONED['containerId'],actualNativeAllSegmentsExported=True,fullNativeExportProofSha256=NATIVE_PROOF_SHA,fullNativeExportStart=AUDIT['start'],fullNativeExportEnd=AUDIT['end'],fullNativeExportSqlBytes=NATIVE['totalSqlBytes'],readinessAttempts=attempt,backupPerformed=False,restorePerformed=False)
write_new(root/'configuration'/('installation-'+generation+'.json'),canonical(out));os.close(lock);print(json.dumps(out))
'''

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--prepare-only',action='store_true');args=parser.parse_args()
 output=TASK/'source-control-binlog-temp-installation.json';assert not output.exists(),'INSTALLATION_ALREADY_RECORDED'
 load=lambda n:json.loads((TASK/n).read_text(encoding='utf-8'))
 original=load('source-control-parent-installation.json');provisioned=load('binlog-tmpfs-tool-provisioned.json');audit=load('binlog-scope-tmpfs-candidate.json');native=load('binlog-tmpfs-full-native-export.json')
 assert all(v['status']=='PASS' for v in (original,provisioned,audit,native)) and not audit['diagnostics']
 assert native['actualNativeAllSegmentsExported'] and native['allActualExitCodesZero'] and native['totalStderrBytes']==0 and native['descriptorPin']==provisioned['descriptorPin']
 assert [r['segment'] for r in native['segments']]==audit['segments'] and native['parentPointPin']==audit['parentPointPin']
 for timestamp in (native['observedAt'],audit['finishedAt']):assert (datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(timestamp)).total_seconds()<900,'PREFLIGHT_STALE'
 pins=load('registered-binlog-tool-restored.json')['failedOriginalPins']
 for history in ('365','366'):pins+=json.loads((PRIVATE/('failed-'+history+'-all-pins.private.json')).read_text(encoding='utf-8'))['pins']
 assert len(pins)==10044
 variables=dict(SOURCE='intruoyi-57-safe-20261024-v1',INSTALLATION=original,PROVISIONED=provisioned,AUDIT=audit,NATIVE=native,NATIVE_PROOF_SHA=hashlib.sha256((TASK/'binlog-tmpfs-full-native-export.json').read_bytes()).hexdigest(),FAILED_PINS=pins)
 script='\n'.join(k+'='+repr(v) for k,v in variables.items())+'\n'+SCRIPT;compile(script,'<binlog-tmpfs-control-activation>','exec')
 if args.prepare_only:
  report=dict(status='PASS',preparedOnly=True,remoteWrites=False,scriptSha256=hashlib.sha256(script.encode()).hexdigest(),failedOriginalFiles=len(pins),engineProgramsChanged=False)
  write(TASK/'binlog-tmpfs-activation-preflight.json',report);print(json.dumps(report));raise SystemExit(0)
 value=remote('172.30.30.57',script,300);write(PRIVATE/'source-control-binlog-temp-installation.private.json',value);public={k:v for k,v in value.items() if k!='sourceSelections'};write(output,public);print(json.dumps(public))
