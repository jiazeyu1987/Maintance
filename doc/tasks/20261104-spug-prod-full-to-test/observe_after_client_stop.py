"""Read /proc only; compare a bounded pair of blocked-process observations."""
import json
import subprocess
from observe_current_state import PRIVATE, PROFILES, TASK

REMOTE = r'''
import collections,datetime,json,os,pathlib,time
clock_ticks=os.sysconf('SC_CLK_TCK')
boot=int(next(line.split()[1] for line in pathlib.Path('/proc/stat').read_text().splitlines() if line.startswith('btime ')))
def snapshot():
 rows=[];counts=collections.Counter();errors=0
 for process in pathlib.Path('/proc').iterdir():
  if not process.name.isdigit():continue
  try:
   status=(process/'status').read_text()
   if '\nState:\tD' not in '\n'+status:continue
   name=next(line.split(':',1)[1].strip() for line in status.splitlines() if line.startswith('Name:'))
   counts[name]+=1
   if not name.startswith('python'):continue
   fields=(process/'stat').read_text().rsplit(')',1)[1].split()
   source='NO_SSH_CONNECTION'
   for field in (process/'environ').read_bytes().split(b'\0'):
    if field.startswith(b'SSH_CONNECTION='):source=field.split(b'=',1)[1].split()[0].decode('ascii','replace')
   started=boot+int(fields[19])/clock_ticks
   rows.append({'pid':int(process.name),'parentPid':int(fields[1]),'name':name,'sshSource':source,
    'startedAt':datetime.datetime.fromtimestamp(started,datetime.timezone.utc).isoformat(),
    'waitChannel':(process/'wchan').read_text().strip()})
  except (OSError,StopIteration,IndexError):errors+=1
 return {'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'blockedByProgram':dict(counts),
  'blockedPythonBySshSource':dict(collections.Counter(row['sshSource'] for row in rows)),
  'latestBlockedPython':sorted(rows,key=lambda row:row['startedAt'])[-5:], 'processes':rows,'readRaceCount':errors}
first=snapshot();time.sleep(10);second=snapshot()
old={r['pid'] for r in first['processes']};new={r['pid'] for r in second['processes']}
print(json.dumps({'first':first,'second':second,'newBlockedPythonPids':sorted(new-old),'departedBlockedPythonPids':sorted(old-new)}))
'''

profile = next(p for p in PROFILES if p['host'] == '172.30.30.57')
args = ['C:/Windows/System32/OpenSSH/ssh.exe', '-F', 'NUL', '-o', 'BatchMode=yes', '-o',
        'StrictHostKeyChecking=yes', '-o', 'IdentitiesOnly=yes', '-i',
        'C:/SpugHandoff/release/private/sshIdentityFile', '-o',
        'UserKnownHostsFile=C:/SpugHandoff/release/private/sshKnownHostsFile', '-o',
        'ConnectTimeout=8', 'root@' + profile['host'], profile['python'] + ' -B -']
result = subprocess.run(args, input=REMOTE.encode('utf-8'), capture_output=True, timeout=30)
if result.returncode:
    (PRIVATE / 'after-client-stop-error.private.txt').write_bytes(result.stderr + result.stdout)
    raise RuntimeError('AFTER_CLIENT_STOP_OBSERVATION_FAILED')
raw = json.loads(result.stdout)
(PRIVATE / 'after-client-stop.private.json').write_text(json.dumps(raw), encoding='utf-8')
report = {key: value for key, value in raw.items() if key not in ('first', 'second')}
for key in ('first', 'second'):
    report[key] = {k: v for k, v in raw[key].items() if k != 'processes'}
(TASK / 'after-client-stop.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))
