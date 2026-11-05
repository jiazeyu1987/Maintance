"""Bounded read-only runtime wait observations; logs remain private."""
import json
import subprocess
from observe_current_state import PRIVATE, PROFILES, TASK

REMOTE = r'''
import collections,datetime,hashlib,json,pathlib,re,subprocess
cid='c4385604eb83b44f2836755bad709581c7e7edd0078b148f3b0f74e0b567304c'
out={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'relatedProcesses':[], 'dockerJournal':[], 'errors':{}}
for directory in pathlib.Path('/proc').iterdir():
 if not directory.name.isdigit():continue
 try:
  cmd=(directory/'cmdline').read_bytes();program=cmd.split(b'\0',1)[0].rsplit(b'/',1)[-1]
  if program!=b'dockerd' and not (program.startswith(b'containerd-shim') and cid.encode() in cmd):continue
  status=(directory/'status').read_text();row={'pid':int(directory.name),'program':program.decode(),'state':next(l.split(':',1)[1].strip() for l in status.splitlines() if l.startswith('State:')),'waitChannel':(directory/'wchan').read_text().strip()}
  tasks=list((directory/'task').iterdir());row['threadCount']=len(tasks)
  row['waitChannelCounts']=dict(collections.Counter((task/'wchan').read_text().strip() for task in tasks[:512] if (task/'wchan').is_file()))
  out['relatedProcesses'].append(row)
 except OSError:pass
try:
 result=subprocess.run(['journalctl','-u','docker','-n','80','--no-pager','-o','json'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5)
 out['journalExitCode']=result.returncode
 for line in result.stdout.decode('utf-8','replace').splitlines():
  try:
   record=json.loads(line);out['dockerJournal'].append({'time':record.get('__REALTIME_TIMESTAMP'),'message':record.get('MESSAGE','')})
  except ValueError:pass
except subprocess.TimeoutExpired:out['errors']['journal']='TIMEOUT_5S'
print(json.dumps(out))
'''

profile = next(p for p in PROFILES if p['host'] == '172.30.30.57')
args = ['C:/Windows/System32/OpenSSH/ssh.exe', '-F', 'NUL', '-o', 'BatchMode=yes', '-o',
        'StrictHostKeyChecking=yes', '-o', 'IdentitiesOnly=yes', '-i',
        'C:/SpugHandoff/release/private/sshIdentityFile', '-o',
        'UserKnownHostsFile=C:/SpugHandoff/release/private/sshKnownHostsFile', '-o',
        'ConnectTimeout=8', 'root@' + profile['host'], profile['python'] + ' -B -']
result = subprocess.run(args, input=REMOTE.encode('utf-8'), capture_output=True, timeout=20)
if result.returncode:
    (PRIVATE / 'backend-wait-error.private.txt').write_bytes(result.stderr + result.stdout)
    raise RuntimeError('BACKEND_WAIT_OBSERVATION_FAILED')
raw = json.loads(result.stdout)
(PRIVATE / 'backend-wait.private.json').write_text(json.dumps(raw), encoding='utf-8')
report = {key: value for key, value in raw.items() if key != 'dockerJournal'}
report['journalMessageCount'] = len(raw['dockerJournal'])
terms = ('c4385604eb83', 'restart', 'mount', 'timeout', 'memory', 'cifs', 'shim', 'deadlock', 'failed', 'error')
report['journalTermCounts'] = {term: sum(term in row['message'].lower() for row in raw['dockerJournal']) for term in terms}
report['journalTimeRange'] = [raw['dockerJournal'][i]['time'] for i in (0, -1)] if raw['dockerJournal'] else []
(TASK / 'backend-wait.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))
