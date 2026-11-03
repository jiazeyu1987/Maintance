"""Read only the active full-release receipt and container states, without lock acquisition."""
from pathlib import Path
import json,subprocess,sys
live=Path('C:/SpugHandoff/release/source/ops/spug/release-center');sys.path.insert(0,str(live))
from intruoyi_runtime import Runtime,ssh_source_bytes
runtime=Runtime(json.loads(Path('C:/SpugHandoff/release/executor.private.json').read_text('utf-8')))
env,job=sys.argv[1:];p=runtime.profile(env)
selection=json.loads(Path(__file__).with_name('selected-release.json').read_text('utf-8'))
source=(live/'intruoyi_remote.py').read_text('utf-8').split("if __name__ == '__main__':")[0]
code=source+'\nimport os\nfrom pathlib import Path\np='+repr(p)+'\njob='+repr(job)+'\ntag='+repr(selection['fullReleaseTag'])+r'''
operations=[]
operation_root=Path(p['stagingRoot'])/('attempts/'+job if p.get('environment')=='prod' else '')
for path in (operation_root/'.operations').glob('OP-*.json'):
    v=json.loads(path.read_text('utf-8'))
    if v.get('jobId')==job:
        row={k:v.get(k) for k in ('operationId','jobId','action','status','phase','startedAt','finishedAt','errorType')}
        pid=v.get('pid');proc=Path('/proc')/str(pid)/'stat';raw=proc.read_text() if proc.exists() else ''
        row['workerAlive']=bool(raw and raw[raw.rfind(')')+2:].split()[19]==v.get('processStart'))
        if row['workerAlive']:
            io=(Path('/proc')/str(pid)/'io').read_text().splitlines()
            row['workerIo']={k:int(value) for k,value in (line.split(':',1) for line in io) if k in ('rchar','read_bytes','wchar')}
            artifacts=[];positions=[]
            for fd in (Path('/proc')/str(pid)/'fd').iterdir():
                try:
                    name=Path(os.readlink(str(fd))).name
                    if name.startswith(('recovery','release.tar')):
                        artifacts.append(name)
                        details=(fd.parent.parent/'fdinfo'/fd.name).read_text().splitlines()
                        position=int(next(line.split(':',1)[1].strip() for line in details if line.startswith('pos:')))
                        positions.append(dict(name=name,position=position,bytes=fd.stat().st_size))
                except FileNotFoundError:pass  # An observed descriptor can close during this read-only snapshot.
            row['openArtifacts']=sorted(set(artifacts))
            row['artifactPositions']=positions
        operations.append(row)
containers={}
for role in ('backend','frontend'):
    v=inspect(p[role]);s=v['State']
    containers[role]=dict(status=s['Status'],running=s['Running'],startedAt=s['StartedAt'],health=s.get('Health',{}).get('Status'))
root=Path(p['stagingRoot'])/tag
if p.get('environment')=='prod':root=Path(p['stagingRoot'])/'attempts'/job/tag
artifacts={v.name:dict(bytes=v.stat().st_size,modifiedAt=v.stat().st_mtime) for v in root.iterdir() if v.is_file() and (v.name.startswith(('recovery-','recovery.sql')) or v.name in ('deployment-progress.private.json','deployment-pending.json'))}
activity=sql(p,"SELECT COMMAND,TIME,COALESCE(STATE,''),CASE WHEN INFO LIKE 'CHECKSUM TABLE%' THEN 'CHECKSUM' WHEN INFO LIKE 'DESCRIBE%' THEN 'DESCRIBE' WHEN INFO LIKE 'SELECT%' THEN 'SELECT' ELSE 'OTHER' END FROM information_schema.PROCESSLIST WHERE ID<>CONNECTION_ID() ORDER BY ID;").splitlines()
processes=[]
for path in Path('/proc').iterdir():
    if not path.name.isdigit():continue
    try:
        name=(path/'comm').read_text().strip()
        if name not in ('mysql','mysqldump','docker','gzip'):continue
        stat=(path/'stat').read_text();fields=stat[stat.rfind(')')+2:].split()
        processes.append(dict(name=name,pid=int(path.name),cpuTicks=int(fields[11])+int(fields[12]),waitChannel=(path/'wchan').read_text().strip()))
    except (FileNotFoundError,ProcessLookupError):continue
print(json.dumps(dict(operations=[v for v in operations if v['action'] in ('deploy','resume-test-deployment-tail')],containers=containers,artifacts=artifacts,databaseActivity=activity,processes=processes)))
'''
r=subprocess.run(['ssh',*runtime.ssh_options(),'root@'+p['host'],p['python']+' -'],input=ssh_source_bytes(code),capture_output=True,timeout=45)
if r.returncode:
    Path('C:/SpugHandoff/release/private/backend-patch-full-release-20261102/progress-'+env+'-'+job+'.stderr.private.log').write_bytes(r.stderr)
assert r.returncode==0,'Full-release progress unavailable'
print(r.stdout.decode('utf-8'))
