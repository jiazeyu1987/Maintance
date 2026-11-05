"""Read source identity and blocked-process evidence without inspecting mounted data."""
import json
from pathlib import Path
import subprocess
from observe_current_state import PRIVATE, PROFILES, TASK
from observe_source_details import public

REMOTE=r'''
import collections,json,pathlib,re
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
out={'capture':json.loads((root/'configuration/capture.json').read_bytes()),'identity':json.loads((root/'configuration/source-identity.json').read_bytes()),'blockedNames':{},'blockedWaitChannels':{},'blockedExamples':[],'mounts':[],'relatedOriginalPids':[]}
names=collections.Counter();channels=collections.Counter()
for directory in pathlib.Path('/proc').iterdir():
 if not directory.name.isdigit():continue
 try:
  status={line.split(':',1)[0]:line.split(':',1)[1].strip() for line in (directory/'status').read_text().splitlines() if ':' in line}
  if not status['State'].startswith('D'):continue
  names[status['Name']]+=1
  channel=(directory/'wchan').read_text().strip();channels[channel]+=1
  if len(out['blockedExamples'])<16:
   cmd=(directory/'cmdline').read_bytes().decode('utf-8','replace')
   out['blockedExamples'].append({'pid':int(directory.name),'ppid':int(status['PPid']),'name':status['Name'],'wchan':channel,'operationIds':sorted(set(re.findall(r'smallapp-[a-z0-9]+',cmd))),
      'stack':(directory/'stack').read_text().splitlines()[:10]})
 except (OSError,KeyError,ValueError):pass
out['blockedNames']=dict(names);out['blockedWaitChannels']=dict(channels)
for line in pathlib.Path('/proc/self/mountinfo').read_text().splitlines():
 pre,post=line.split(' - ',1);parts=pre.split();after=post.split()
 if after[0] in ('cifs','nfs','nfs4') or parts[4] in ('/var/lib/docker','/mnt/nas'):
  out['mounts'].append({'mountId':parts[0],'parentId':parts[1],'mountPoint':parts[4],'filesystem':after[0],'source':after[1]})
for directory in (root/'ledger').iterdir():
 if not directory.is_dir():continue
 processpath=directory/'worker-process.json'
 if not processpath.is_file():continue
 value=json.loads(processpath.read_bytes());pid=value['pid'];proc=pathlib.Path('/proc')/str(pid)
 matches=False
 if proc.is_dir():
  try:matches=directory.name.encode() in (proc/'cmdline').read_bytes()
  except OSError:pass
 out['relatedOriginalPids'].append({'operationId':directory.name,'pid':pid,'pidExists':proc.is_dir(),'originalCommandMatches':matches,'workerTerminalExists':(directory/'worker-terminal.json').is_file()})
print(json.dumps(out))
'''

profile=next(p for p in PROFILES if p['host']=='172.30.30.57')
args=['C:/Windows/System32/OpenSSH/ssh.exe','-F','NUL','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','IdentitiesOnly=yes','-i','C:/SpugHandoff/release/private/sshIdentityFile','-o','UserKnownHostsFile=C:/SpugHandoff/release/private/sshKnownHostsFile','-o','ConnectTimeout=8','root@'+profile['host'],profile['python']+' -B -']
p=subprocess.run(args,input=REMOTE.encode('utf-8'),capture_output=True,timeout=30)
if p.returncode:
    (PRIVATE/'source-runtime-error.private.txt').write_bytes(p.stderr+p.stdout)
    raise RuntimeError('SOURCE_RUNTIME_READ_FAILED')
raw=json.loads(p.stdout)
(PRIVATE/'source-runtime.private.json').write_text(json.dumps(raw),encoding='utf-8')
report=public(raw)
(TASK/'source-runtime.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
