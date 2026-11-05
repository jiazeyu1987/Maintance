"""Read the exact source owner and top-level operation/PID evidence, no mutations."""
import json
from pathlib import Path
import re
import subprocess
from observe_current_state import PRIVATE, PROFILES, TASK

REMOTE=r'''
import collections,hashlib,json,pathlib,re,subprocess
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
control=json.loads((root/'configuration/control.json').read_bytes())
out={'ownerConfigurations':{},'operations':[],'relatedProcesses':[],'processCounts':{},'load':pathlib.Path('/proc/loadavg').read_text().strip()}
for ref,pin in control['sourceConfigurations'].items():
 raw=pathlib.Path(pin['path']).read_bytes()
 assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256']
 out['ownerConfigurations'][ref]={'pin':pin,'value':json.loads(raw)}
for directory in sorted((root/'ledger').iterdir(),key=lambda p:p.stat().st_mtime):
 if not directory.is_dir():continue
 row={'operationId':directory.name,'files':sorted(p.name for p in directory.iterdir()),'documents':{}}
 for path in directory.glob('*.json'):
  if path.stat().st_size<200000:
   try:row['documents'][path.name]=json.loads(path.read_bytes())
   except (OSError,ValueError):row['documents'][path.name]={'observationError':'INVALID_JSON'}
 out['operations'].append(row)
states=collections.Counter();threads=[]
for directory in pathlib.Path('/proc').iterdir():
 if not directory.name.isdigit():continue
 try:
  status={line.split(':',1)[0]:line.split(':',1)[1].strip() for line in (directory/'status').read_text().splitlines() if ':' in line}
  states[status['State']]+=1
  row={'pid':int(directory.name),'name':status['Name'],'state':status['State'],'ppid':int(status['PPid']),'threads':int(status['Threads'])}
  threads.append(row)
  cmd=(directory/'cmdline').read_bytes()
  if str(root).encode() in cmd:
   row.update(operationIds=sorted(set(re.findall(r'smallapp-[a-z0-9]+',cmd.decode('utf-8','replace')))),commandSha256=hashlib.sha256(cmd).hexdigest())
   out['relatedProcesses'].append(row)
 except (OSError,KeyError,ValueError):pass
out['processCounts']=dict(states);out['largestThreadCounts']=sorted(threads,key=lambda p:p['threads'],reverse=True)[:8]
out['memory']={line.split(':')[0]:line.split(':',1)[1].strip() for line in pathlib.Path('/proc/meminfo').read_text().splitlines() if line.split(':')[0] in ('MemTotal','MemAvailable','SwapTotal','SwapFree')}
print(json.dumps(out))
'''


def public(value):
    if isinstance(value,dict):
        return {key:('[REDACTED]' if re.search(r'password|token|secret|credential|auth|environment|argv',key,re.I) else public(item)) for key,item in value.items()}
    if isinstance(value,list):return [public(item) for item in value]
    return value


if __name__=='__main__':
    profile=next(p for p in PROFILES if p['host']=='172.30.30.57')
    args=['C:/Windows/System32/OpenSSH/ssh.exe','-F','NUL','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','IdentitiesOnly=yes','-i','C:/SpugHandoff/release/private/sshIdentityFile','-o','UserKnownHostsFile=C:/SpugHandoff/release/private/sshKnownHostsFile','-o','ConnectTimeout=8','root@'+profile['host'],profile['python']+' -B -']
    p=subprocess.run(args,input=REMOTE.encode('utf-8'),capture_output=True,timeout=30)
    if p.returncode:
        (PRIVATE/'source-details-error.private.txt').write_bytes(p.stderr+p.stdout)
        raise RuntimeError('SOURCE_DETAILS_READ_FAILED')
    raw=json.loads(p.stdout)
    (PRIVATE/'source-details.private.json').write_text(json.dumps(raw),encoding='utf-8')
    report=public(raw)
    (TASK/'source-details.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    for row in report['operations']:
        selected={name:{key:doc.get(key) for key in ('operationId','state','status','phase','pid','actualExitCode','errorCode','failureCode') if key in doc} for name,doc in row['documents'].items() if isinstance(doc,dict)}
        print(json.dumps({'operationId':row['operationId'],'files':row['files'],'documents':selected}))
    print(json.dumps({key:report[key] for key in ('load','relatedProcesses','processCounts','largestThreadCounts','memory','ownerConfigurations')},ensure_ascii=False))
