"""Read only the original remote receipt, worker identity and known staging files."""
from datetime import datetime
from pathlib import Path
import json
import shlex
import sqlite3
import subprocess
import sys

task=Path(__file__).parent
c=json.loads(Path('C:/SpugHandoff/release/executor.private.json').read_text('utf-8-sig'))
assert len(sys.argv)==3 and sys.argv[2]=='--deploy'
candidate=''
if len(sys.argv)==3 and sys.argv[2]!='--deploy':
 import ast
 assert sys.argv[2]=='--candidate'
 source=Path('C:/SpugHandoff/release/maintenance-release-20261031/ops/spug/release-center/intruoyi_recovery_agent.py').read_text('utf-8')
 node=next(node for node in ast.parse(source).body if isinstance(node,ast.FunctionDef) and node.name=='archive_member_name')
 candidate=ast.get_source_segment(source,node)
with sqlite3.connect('file:'+str(Path(c['stateDir'])/'state.sqlite3')+'?mode=ro',uri=True) as db:
    state=json.loads(db.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
j=next(row for row in state['jobs'] if row['id']==sys.argv[1])
op=next(row for row in j['remoteOperations'] if row['action']=='deploy') if len(sys.argv)==3 and sys.argv[2]=='--deploy' else j['remoteOperations'][-1]
p=c['targets'][op['env']]
root=j.get('runtimeStagingRoots',{}).get(op['env'],p['stagingRoot'])
payload=dict(root=root,operationId=op['operationId'],jobId=j['id'],tag=j.get('releaseTag'))
code=r'''import json,os,hashlib,tarfile
from pathlib import Path
p=PAYLOAD
root=Path(p['root'])
receipt=root/'.operations'/(p['operationId']+'.json')
result=dict(operationId=p['operationId'],receiptExists=receipt.is_file())
if receipt.is_file():
 value=json.loads(receipt.read_text('utf-8'))
 assert value['jobId']==p['jobId'] and value['operationId']==p['operationId']
 result.update({k:value.get(k) for k in ('status','action','startedAt','finishedAt','errorType')})
 stat=Path('/proc')/str(value['pid'])/'stat'
 raw=stat.read_text() if stat.exists() else ''
 result['originalWorkerAlive']=bool(raw) and raw[raw.rfind(')')+2:].split()[19]==value['processStart']
 if raw:
  fields=raw[raw.rfind(')')+2:].split()
  result['workerCpuSeconds']=round((int(fields[11])+int(fields[12]))/os.sysconf('SC_CLK_TCK'),2)
  io_path=Path('/proc')/str(value['pid'])/'io'
  if io_path.exists():
   counters=dict(line.split(':',1) for line in io_path.read_text().splitlines())
   result['workerReadBytes']=int(counters.get('read_bytes','0'))
   result['workerReadCharacters']=int(counters.get('rchar','0'))
  children=Path('/proc')/str(value['pid'])/'task'/str(value['pid'])/'children'
  child_ids=children.read_text().split()
  result['workerChildPids']=[int(child) for child in child_ids]
  result['workerChildNames']=[(Path('/proc')/child/'comm').read_text().strip() for child in child_ids if (Path('/proc')/child/'comm').exists()]
  # Never emit raw argv: database commands may contain private authentication.
  kinds=[]
  for child in child_ids:
   cmd=Path('/proc')/child/'cmdline'
   if cmd.exists():
    argv=cmd.read_bytes().replace(b'\0',b' ').lower()
    kinds.append('database-dump' if b'mysqldump' in argv else 'database-client' if b'mysql' in argv else 'container-control' if b'docker' in argv else 'other')
  result['workerChildKinds']=kinds
folder=root/p['tag'] if p.get('tag') else root
progress=folder/'deployment-progress.private.json'
if progress.is_file():
 value=json.loads(progress.read_text('utf-8'))
 result['deploymentProgress']={key:value[key] for key in ('phase','status','step','migrationId','sqlStarted','sqlCompleted','containersReplaced','snapshotComplete','updatedAt') if key in value}
names=('release.tar','images.tar','recovery.sql.gz','recovery.sql','recovery.incomplete.sql.gz','recovery.incomplete.sql',
       'recovery-volume-0.tar','recovery-volume-1.tar','recovery-record.private.json','deployment-pending.json')
result['files']=[dict(name=name,bytes=(folder/name).stat().st_size) for name in names if (folder/name).is_file()]
ack=folder/'external-recovery.private.json'
if ack.is_file():
 value=json.loads(ack.read_text('utf-8'))
 assert value['releaseTag']==p['tag']
 result['externalRecovery']={key:value.get(key) for key in ('mode','operatorConfirmed','releaseTag','packageIdentity','originFingerprint')}
result['checkpointRecordExists']=(folder/'recovery-record.private.json').is_file()
result['recoveryAttempts']=[]
for path in folder.glob('recovery-JOB-*/receipt.private.json'):
 value=json.loads(path.read_text('utf-8'))
 assert value['releaseTag']==p['tag']
 row={k:value.get(k) for k in ('jobId','originalJobId','phase','status','startedAt','finishedAt','errorCategory')}
 row['retainedDataVolumes']=len(value.get('retainedData',[]))
 row['volumeJournals']=[]
 origin=json.loads((folder/'recovery-record.private.json').read_text('utf-8'))
 for resource in origin['resources']:
  source=Path(resource['mount']['Source'])
  journal=source.parent/(source.name+'.restore-'+value['jobId']+'.json')
  if journal.is_file():
   entry=json.loads(journal.read_text('utf-8'))
   assert entry['binding']['attemptId']==value['jobId']
   row['volumeJournals'].append(dict(role=resource['role'],phase=entry['phase']))
 row['failedDatabaseCaptures']=[dict(relativePath=str(f.relative_to(folder)),bytes=f.stat().st_size) for f in path.parent.glob('failed-database-*/recovery.sql.gz')]
 result['recoveryAttempts'].append(row)
s=os.statvfs(root)
result['availableBytes']=s.f_bavail*s.f_frsize
if p.get('inspectArchives'):
 from pathlib import PurePosixPath
 def require(condition,message):
  if not condition: raise RuntimeError(message)
 if CANDIDATE_FUNCTION: exec(CANDIDATE_FUNCTION,globals())
 result['archiveValidation']=[]
 for name in ('recovery-volume-0.tar','recovery-volume-1.tar'):
  path=folder/name
  if not path.is_file(): continue
  seen=set();bad=[];count=0;hardlinks=0;candidate_seen=set();candidate_rejected=0;trailing_only=0
  with tarfile.open(path,'r:') as archive:
   for member in archive:
    count+=1;part=PurePosixPath(member.name)
    reasons=[]
    if not member.name or part.is_absolute() or '..' in part.parts or str(part)!=member.name: reasons.append('unsafe-name')
    if member.name in seen: reasons.append('duplicate')
    if not (member.isdir() or member.isfile()): reasons.append('non-regular-type')
    if member.issparse(): reasons.append('sparse')
    if member.islnk(): hardlinks+=1
    if member.isdir() and str(part)+'/'==member.name: trailing_only+=1
    if CANDIDATE_FUNCTION:
     try:
      canonical=archive_member_name(member)
      if canonical in candidate_seen: candidate_rejected+=1
      candidate_seen.add(canonical)
     except RuntimeError: candidate_rejected+=1
    if reasons:
     target=PurePosixPath(member.linkname)
     bad.append(dict(nameSha256=hashlib.sha256(member.name.encode()).hexdigest(),reasons=reasons,directory=member.isdir(),endsWithSlash=member.name.endswith('/'),singleTrailingSlashOnly=member.isdir() and str(part)+'/'==member.name,absolute=part.is_absolute(),parentTraversal='..' in part.parts,hardlink=member.islnk(),targetPreviouslySeen=member.linkname in seen,targetPathSafe=bool(member.linkname) and not target.is_absolute() and '..' not in target.parts and str(target)==member.linkname))
    seen.add(member.name)
  result['archiveValidation'].append(dict(name=name,members=count,hardlinks=hardlinks,violations=bad[:3],violationCount=len(bad),singleTrailingSlashDirectories=trailing_only,candidateChecked=bool(CANDIDATE_FUNCTION),candidateRejected=candidate_rejected))
result['mutations']=False
print(json.dumps(result))
'''.replace('PAYLOAD',repr(dict(payload,inspectArchives=j['status']=='failed' and j['action']=='recover-release'))).replace('CANDIDATE_FUNCTION',repr(candidate))
args=['ssh','-F','NUL','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=10',
      '-o','IdentitiesOnly=yes','-o','UserKnownHostsFile='+c['sshKnownHostsFile'],'-i',c['sshIdentityFile'],
      'root@'+p['host'],shlex.quote(p['python'])+' -c '+shlex.quote(code)]
r=subprocess.run(args,capture_output=True,encoding='utf-8',timeout=35)
assert r.returncode==0, 'Read-only original-operation observation failed'
report=dict(time=datetime.now().astimezone().isoformat(),jobId=j['id'],host=p['host'],**json.loads(r.stdout))
(task/('remote-'+j['id']+'-latest.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
