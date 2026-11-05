"""Observe the original repository operation by its contracted SHA-256 directory."""
import json
import subprocess
from observe_current_state import PRIVATE, PROFILES, TASK

REMOTE = r'''
import hashlib,json,pathlib,re
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
op='smallapp-3d4c7ab0f65841b8892e4a640a53176d'
config_path=root/'request-configurations'/op/'repository.json'
config=json.loads(config_path.read_bytes())
operation_root=pathlib.Path(config['operationRoot'])
if root not in operation_root.parents:raise RuntimeError('OPERATION_ROOT_OUTSIDE_LOCAL_CONTROL')
directory=operation_root/hashlib.sha256(op.encode()).hexdigest()
out={'operationId':op,'operationDirectory':str(directory),'fileCount':0, 'documents':{},'processes':[]}
if directory.is_dir():
 names=sorted(p.name for p in directory.iterdir());out['fileCount']=len(names)
 queries=[(int(re.match(r'capture-query-([0-9]+)-terminal.json$',name).group(1)),name) for name in names if re.match(r'capture-query-([0-9]+)-terminal.json$',name)]
 selected=['start.json','request.json','worker-process.json','result.json','capture-terminal.json']
 if queries:selected.append(max(queries)[1]);out['captureQueryTerminalCount']=len(queries)
 for name in selected:
  path=directory/name
  if path.is_file() and path.stat().st_size<1000000:out['documents'][name]=json.loads(path.read_bytes())
 for name,doc in out['documents'].items():
  if not isinstance(doc,dict) or type(doc.get('pid')) is not int:continue
  process=pathlib.Path('/proc')/str(doc['pid']);row={'evidence':name,'pid':doc['pid'],'exists':process.exists()}
  if process.exists():
   try:
    cmd=(process/'cmdline').read_bytes();status=(process/'status').read_text()
    row.update(commandSha256=hashlib.sha256(cmd).hexdigest(),referencesOperationDirectory=str(directory).encode() in cmd,
      state=next(l.split(':',1)[1].strip() for l in status.splitlines() if l.startswith('State:')),
      waitChannel=(process/'wchan').read_text().strip())
   except OSError:row['observation']='PROCESS_CHANGED_DURING_OBSERVATION'
  out['processes'].append(row)
print(json.dumps(out))
'''

profile = next(p for p in PROFILES if p['host'] == '172.30.30.57')
args = ['C:/Windows/System32/OpenSSH/ssh.exe', '-F', 'NUL', '-o', 'BatchMode=yes',
        '-o', 'StrictHostKeyChecking=yes', '-o', 'IdentitiesOnly=yes', '-i',
        'C:/SpugHandoff/release/private/sshIdentityFile', '-o',
        'UserKnownHostsFile=C:/SpugHandoff/release/private/sshKnownHostsFile', '-o',
        'ConnectTimeout=8', 'root@' + profile['host'], profile['python'] + ' -B -']
result = subprocess.run(args, input=REMOTE.encode('utf-8'), capture_output=True, timeout=20)
if result.returncode:
    (PRIVATE / 'original-operation-error.private.txt').write_bytes(result.stderr + result.stdout)
    raise RuntimeError('ORIGINAL_OPERATION_OBSERVATION_FAILED')
raw = json.loads(result.stdout)
(PRIVATE / 'original-operation.private.json').write_text(json.dumps(raw), encoding='utf-8')
report = {key: value for key, value in raw.items() if key != 'documents'}
report['results'] = {name: {key: doc[key] for key in
    ('state', 'failureCode', 'actualExitCode', 'finishedAt', 'pid', 'operationId') if key in doc}
    for name, doc in raw['documents'].items()}
(TASK / 'original-operation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))
