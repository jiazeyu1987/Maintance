"""Read-only CIFS/operation diagnostics; never statfs, mount, unmount, stop or retry."""
import json
import subprocess
from observe_current_state import PRIVATE, PROFILES, TASK
from observe_source_details import public

REMOTE=r'''
import collections,hashlib,json,pathlib,re,socket,subprocess
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
op='smallapp-3d4c7ab0f65841b8892e4a640a53176d'
out={'operationId':op,'originalDocuments':{},'originalFiles':{},'blockedCommandGroups':{},'errors':{}}
for name in ('repository-operations','capture-staging'):
 directory=root/name/op
 if not directory.is_dir():continue
 out['originalFiles'][name]=sorted(p.name for p in directory.iterdir())
 for filename in ('operation.json','terminal-result.json','source-restoration.json','worker-process.json','worker-completion.json','result.json','terminal.json'):
  path=directory/filename
  if path.is_file() and path.stat().st_size<1000000:
   out['originalDocuments'][name+'/'+filename]=json.loads(path.read_bytes())
groups={}
for directory in pathlib.Path('/proc').iterdir():
 if not directory.name.isdigit():continue
 try:
  status=(directory/'status').read_text()
  if '\nState:\tD' not in '\n'+status:continue
  cmd=(directory/'cmdline').read_bytes();digest=hashlib.sha256(cmd).hexdigest()
  if digest in groups:groups[digest]['count']+=1;continue
  argv=cmd.decode('utf-8','replace').split('\x00');environ=(directory/'environ').read_bytes().decode('utf-8','replace').split('\x00')
  groups[digest]={'count':1,'samplePid':int(directory.name),'program':argv[0],
    'argumentCount':len(argv),'usesStatvfs':b'statvfs' in cmd,'usesDiskUsage':b'disk_usage' in cmd,
    'inlineFunctionNames':re.findall(r'def ([A-Za-z_][A-Za-z_0-9]*)\(',cmd.decode('utf-8','replace')),
    'knownPathMentions':[s for s in ('/mnt/nas','/mnt/intruoyi-backup-nas','prod57-spug-rehearsal-20261021/nas') if s.encode() in cmd],
    'sshConnection':[s for s in environ if s.startswith(('SSH_CLIENT=','SSH_CONNECTION='))]}
 except OSError:pass
out['blockedCommandGroups']=groups
try:
 with socket.create_connection(('172.30.30.4',445),2):out['nasTcp445']='CONNECTED'
except Exception as e:out['nasTcp445']=type(e).__name__
try:
 debug=pathlib.Path('/proc/fs/cifs/DebugData').read_text()
 out['cifsDebugRaw']=debug
 out['cifsDebugSummary']=[l.strip() for l in debug.splitlines() if any(s in l.lower() for s in ('tcp status','need_reconnect','mounts:','connectionid','sessions:','server:','share:'))]
except OSError as e:out['errors']['cifsDebug']=type(e).__name__
try:
 result=subprocess.run(['dmesg','--notime'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5)
 out['kernelCifsEvents']=[line for line in result.stdout.decode('utf-8','replace').splitlines() if 'CIFS' in line or 'SMB' in line][-18:]
except Exception as e:out['errors']['kernelEvents']=type(e).__name__
print(json.dumps(out))
'''

profile=next(p for p in PROFILES if p['host']=='172.30.30.57')
args=['C:/Windows/System32/OpenSSH/ssh.exe','-F','NUL','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','IdentitiesOnly=yes','-i','C:/SpugHandoff/release/private/sshIdentityFile','-o','UserKnownHostsFile=C:/SpugHandoff/release/private/sshKnownHostsFile','-o','ConnectTimeout=8','root@'+profile['host'],profile['python']+' -B -']
p=subprocess.run(args,input=REMOTE.encode('utf-8'),capture_output=True,timeout=30)
if p.returncode:
    (PRIVATE/'source-host-error.private.txt').write_bytes(p.stderr+p.stdout)
    raise RuntimeError('SOURCE_HOST_DIAGNOSIS_FAILED')
raw=json.loads(p.stdout)
(PRIVATE/'source-host-diagnostics.private.json').write_text(json.dumps(raw),encoding='utf-8')
report=public({key:item for key,item in raw.items() if key!='cifsDebugRaw'})
(TASK/'source-host-diagnostics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
out={key:item for key,item in report.items() if key!='originalDocuments'}
out['originalResults']={key:{k:doc[k] for k in ('state','phase','status','actualExitCode','failureCode','data') if k in doc} for key,doc in report['originalDocuments'].items()}
print(json.dumps(out,ensure_ascii=False))
