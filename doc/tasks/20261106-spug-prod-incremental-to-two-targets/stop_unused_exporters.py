"""Stop only the two unregistered task tools, retaining both failure containers."""
import argparse,hashlib,json
from common import TASK,PRIVATE,remote,write

SCRIPT=r'''
import datetime,hashlib,json,pathlib,subprocess
def run(args):
 p=subprocess.run(args,capture_output=True,timeout=25)
 assert p.returncode==0 and not p.stderr,'OWN_EXPORTER_COMMAND_FAILED'
 return p.stdout
def snapshot():
 ids=run(['docker','ps','-aq','--no-trunc']).decode().split()
 return {r['Id']:r for r in json.loads(run(['docker','inspect',*ids]))}
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def definition(row):return {k:row[k] for k in ('Path','Args','HostConfig','Config','Image')}|dict(Mounts=sorted(row['Mounts'],key=lambda m:m['Destination']))
def runtime(row):return dict(state={k:row['State'][k] for k in ('Running','Paused','Restarting','Pid','StartedAt','FinishedAt')},restartCount=row['RestartCount'],networks=row['NetworkSettings']['Networks'])
assert not pathlib.Path('/var/lib/spug-restore-resources/active.json').exists(),'ACTIVE_SOURCE_RESERVATION'
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
for process in pathlib.Path('/proc').iterdir():
 if not process.name.isdecimal():continue
 try:command=(process/'cmdline').read_bytes()
 except (FileNotFoundError,ProcessLookupError):continue
 if str(root).encode() in command:assert b'control_entry.py' in command,'ACTIVE_SOURCE_WORKER'
before=snapshot();owned={r['containerId']:r for r in INVENTORY['containers']}
assert len(before)==198 and len(owned)==3 and set(owned)<=set(before),'CONTAINER_SET_CHANGED'
registered=INVENTORY['registeredContainerId'];unused=[i for i,r in owned.items() if not r['registered']]
assert len(unused)==2 and registered not in unused
for identity,expected in owned.items():
 row=before[identity]
 assert digest(definition(row))==expected['definitionSha256'] and digest(runtime(row))==expected['runtimeSha256'],'OWN_EXPORTER_DRIFT'
 assert row['Name']=='/'+expected['name'] and row['Path']=='sleep' and row['Args']==['infinity']
 assert row['Config']['Labels']['spug.component']=='mysqlbinlog-exporter'
 top=run(['docker','top',identity]).decode().splitlines()
 assert len(top)==2 and top[0].split()==['UID','PID','PPID','C','STIME','TTY','TIME','CMD'],'OWN_EXPORTER_ACTIVE_CHILD'
 assert top[1].split()[1]==str(row['State']['Pid']),'OWN_EXPORTER_INIT_PID_CHANGED'
 assert pathlib.Path('/proc',str(row['State']['Pid']),'cmdline').read_bytes().rstrip(b'\0').split(b'\0')==[b'/usr/bin/coreutils',b'--coreutils-prog-shebang=sleep',b'/usr/bin/sleep',b'infinity'],'OWN_EXPORTER_INIT_COMMAND_CHANGED'
for identity in unused:
 assert run(['docker','stop','--time','10',identity]).decode().strip()==identity,'OWN_EXPORTER_STOP_REJECTED'
after=snapshot();assert set(after)==set(before),'CONTAINER_SET_CHANGED'
for identity,row in before.items():
 assert digest(definition(after[identity]))==digest(definition(row)),'CONTAINER_DEFINITION_CHANGED'
 if identity not in unused:assert runtime(after[identity])==runtime(row),'OTHER_CONTAINER_RUNTIME_CHANGED'
entries=[]
for identity in unused:
 row=after[identity];assert not row['State']['Running'] and not row['State']['Paused'] and not row['State']['Restarting'] and row['State']['Pid']==0,'OWN_EXPORTER_NOT_STOPPED'
 entries.append(dict(containerId=identity,name=owned[identity]['name'],stopped=True,retained=True,afterRuntimeSha256=digest(runtime(row))))
assert after[registered]['State']['Running'],'REGISTERED_EXPORTER_NOT_RUNNING'
print(json.dumps(dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),backupOperationId=BACKUP,containers=entries,registeredExporterRunning=True,allOriginalAndRegisteredContainersPreserved=True,noContainersDeleted=True,noImagesOrDataChanged=True)))
'''

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--prepare-only',action='store_true');args=parser.parse_args()
 destination=TASK/'unused-exporters-stopped.json';assert not destination.exists(),'STOP_ALREADY_RECORDED'
 inventory=json.loads((TASK/'source-added-exporters.json').read_text(encoding='utf-8'))
 point=json.loads((TASK/'new-incremental-point-verified.json').read_text(encoding='utf-8'))
 assert point['status']=='PASS' and point['actualExitCode']==0
 for suffix in ('58','59'):
  native=json.loads((TASK/('restore-'+suffix+'-native-evidence.json')).read_text(encoding='utf-8'))
  assert native['status']=='PASS' and native['actualExitCode']==0 and native['backupOperationId']==point['operationId']
 variables=dict(INVENTORY=inventory,BACKUP=point['operationId'])
 script='\n'.join(k+'='+repr(v) for k,v in variables.items())+'\n'+SCRIPT;compile(script,'<stop-unused-exporters>','exec')
 if args.prepare_only:
  report=dict(status='PASS',preparedOnly=True,remoteWrites=False,scriptSha256=hashlib.sha256(script.encode()).hexdigest(),containerIds=[r['containerId'] for r in inventory['containers'] if not r['registered']])
  write(TASK/'unused-exporters-stop-preflight.json',report)
 else:
  report=remote('172.30.30.57',script,120);write(PRIVATE/'unused-exporters-stopped.private.json',report);write(destination,report)
 print(json.dumps(report))
