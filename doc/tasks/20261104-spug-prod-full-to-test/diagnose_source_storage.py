"""Read-only local mount contracts, SMB session state and host resource evidence."""
import json
import subprocess
from observe_current_state import PRIVATE, PROFILES, TASK

REMOTE = r'''
import collections,datetime,json,os,pathlib,re,socket,subprocess
out={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'kernel':os.uname().release,
     'uptimeSeconds':pathlib.Path('/proc/uptime').read_text().split()[0],
     'load':pathlib.Path('/proc/loadavg').read_text().split()[:3],'memory':{},'containers':{},'dockerThreads':[], 'errors':{}}
for line in pathlib.Path('/proc/meminfo').read_text().splitlines():
 key,value=line.split(':',1)
 if key in ('MemTotal','MemFree','MemAvailable','SwapTotal','SwapFree','Slab','SReclaimable','SUnreclaim','Dirty','Writeback','CommitLimit','Committed_AS'):out['memory'][key]=value.strip()
out['cifsMounts']=[line for line in pathlib.Path('/proc/self/mountinfo').read_text().splitlines() if ' - cifs ' in line]
roles={'backend':'c4385604eb83b44f2836755bad709581c7e7edd0078b148f3b0f74e0b567304c','redis':'5099e7bd566ec6a683e8842b84d8db9e41245708fce29e89309607d6a7e72653'}
for role,cid in roles.items():
 root=pathlib.Path('/var/lib/docker/containers')/cid
 try:
  config=json.loads((root/'config.v2.json').read_bytes());host=json.loads((root/'hostconfig.json').read_bytes())
  out['containers'][role]={'name':config.get('Name'),'mountPoints':config.get('MountPoints'),
    'binds':host.get('Binds'),'restartPolicy':host.get('RestartPolicy'),
    'persistedState':{k:config.get('State',{}).get(k) for k in ('Running','Restarting','Pid','ExitCode','OOMKilled','StartedAt','FinishedAt')},
    'memoryLimit':host.get('Memory'),'memorySwap':host.get('MemorySwap')}
 except (OSError,ValueError) as error:out['errors'][role]=type(error).__name__
for directory in pathlib.Path('/proc').iterdir():
 if not directory.name.isdigit():continue
 try:
  program=(directory/'cmdline').read_bytes().split(b'\0',1)[0].rsplit(b'/',1)[-1]
  if program!=b'dockerd':continue
  for task in (directory/'task').iterdir():
   wait=(task/'wchan').read_text().strip()
   if 'smb' not in wait and 'cifs' not in wait:continue
   out['dockerThreads'].append({'pid':int(directory.name),'tid':int(task.name),'waitChannel':wait,'stack':(task/'stack').read_text().splitlines()[:18]})
 except OSError:pass
try:
 raw=pathlib.Path('/proc/fs/cifs/DebugData').read_text()
 out['cifsDebugRaw']=raw
 out['cifsStatus']=[l.strip() for l in raw.splitlines() if any(term in l.lower() for term in ('tcp status','mounts:','credits','connectionid','dialect','in flight'))]
except OSError as error:out['errors']['cifsDebug']=type(error).__name__
try:
 result=subprocess.run(['journalctl','-k','-b','-n','2500','--no-pager','-o','json'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=8)
 rows=[]
 for line in result.stdout.decode('utf-8','replace').splitlines():
  try:
   row=json.loads(line);message=row.get('MESSAGE','')
   if re.search(r'cifs|smb|out of memory|oom-kill|killed process|blocked for more than|I/O error',message,re.I):rows.append({'time':row.get('__REALTIME_TIMESTAMP'),'message':message})
  except ValueError:pass
 out['kernelEventsRaw']=rows
 out['kernelEventCounts']={term:sum(term in r['message'].lower() for r in rows) for term in ('cifs','smb','out of memory','oom-kill','killed process','blocked for more than','i/o error')}
 out['journalExitCode']=result.returncode
except subprocess.TimeoutExpired:out['errors']['kernelJournal']='TIMEOUT_8S'
try:
 with socket.create_connection(('172.30.30.4',445),2):out['nasTcp445']='CONNECTED'
except Exception as error:out['nasTcp445']=type(error).__name__
print(json.dumps(out))
'''

profile = next(p for p in PROFILES if p['host'] == '172.30.30.57')
args = ['C:/Windows/System32/OpenSSH/ssh.exe', '-F', 'NUL', '-o', 'BatchMode=yes', '-o',
        'StrictHostKeyChecking=yes', '-o', 'IdentitiesOnly=yes', '-i',
        'C:/SpugHandoff/release/private/sshIdentityFile', '-o',
        'UserKnownHostsFile=C:/SpugHandoff/release/private/sshKnownHostsFile', '-o',
        'ConnectTimeout=15', 'root@' + profile['host'], profile['python'] + ' -B -']
result = subprocess.run(args, input=REMOTE.encode('utf-8'), capture_output=True, timeout=40)
if result.returncode:
    (PRIVATE / 'storage-diagnosis-error.private.txt').write_bytes(result.stderr + result.stdout)
    raise RuntimeError('STORAGE_DIAGNOSIS_FAILED')
raw = json.loads(result.stdout)
(PRIVATE / 'storage-diagnosis.private.json').write_text(json.dumps(raw), encoding='utf-8')
report = {key: value for key, value in raw.items() if key not in ('cifsDebugRaw','cifsMounts','kernelEventsRaw','containers')}
report['cifsMounts'] = [{'mountPoint':row.split(' - ',1)[0].split()[4],
                        'source':row.split(' - ',1)[1].split()[1]} for row in raw['cifsMounts']]
report['containers'] = {}
for role, container in raw['containers'].items():
    safe = {key:value for key,value in container.items() if key != 'mountPoints'}
    safe['mountPoints'] = {key:{k:value[k] for k in ('Type','Name','Source','Destination','RW','Driver') if k in value}
                          for key,value in (container.get('mountPoints') or {}).items()}
    report['containers'][role] = safe
(TASK / 'storage-diagnosis.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))
