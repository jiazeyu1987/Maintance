"""Small read-only summary of recorded build progress, no raw subprocess output."""
from pathlib import Path
import json,sqlite3,sys,psutil
with sqlite3.connect('file:C:/SpugHandoff/release/state/state.sqlite3?mode=ro',uri=True) as db:state=json.loads(db.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
job=next(j for j in state['jobs'] if j['id']==sys.argv[1])
result={k:job[k] for k in ('id','status','currentStep','buildDirectory','buildWorktree','buildWorktreeCleanup') if k in job}
if job.get('sealedPackage'):
    package=job['sealedPackage']
    result['sealedPackage']={k:package[k] for k in ('releaseTag','gitCommit','directory','jarBytes','packageSha256','nasDirectory') if k in package}
result['liveChildren']=[]
for item in job.get('localProcesses',[]):
    try:
        process=psutil.Process(item['pid'])
        if process.create_time()==item['createdAt']:
            result['liveChildren'].append(dict(pid=process.pid,name=process.name(),cpuSeconds=round(sum(process.cpu_times()[:2]),1)))
    except psutil.NoSuchProcess:pass
print(json.dumps(result))
