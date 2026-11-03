"""Verify installed code and untouched prior history while the explicit retry runs."""
from pathlib import Path
import hashlib,json,sqlite3,psutil
root=Path('C:/SpugHandoff/release');private=root/'private/backend-patch-full-release-20261102/runtime-stopped-patch'
before=json.loads((private/'before.json').read_text('utf-8'))
assert hashlib.sha256((root/'executor.private.json').read_bytes()).hexdigest()==before['configSha256']
for row in json.loads((private/'code-update-plan.json').read_text('utf-8')):
    assert hashlib.sha256((root/'source/ops/spug/release-center'/row['name']).read_bytes()).hexdigest()==row['afterSha256']
owners={c.pid for c in psutil.net_connections(kind='tcp') if c.status=='LISTEN' and c.laddr.port==18112}
assert len(owners)==1
pid=owners.pop();process=psutil.Process(pid)
assert (root/'source/ops/spug/release-center/intruoyi_executor.py').as_posix() in [v.replace('\\','/') for v in process.cmdline()]
def read(path):
    with sqlite3.connect('file:'+path.as_posix()+'?mode=ro',uri=True) as db:
        return json.loads(db.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
old=read(private/'state-before.private.sqlite3');current=read(root/'state/state.sqlite3')
newjobs={j['id']:j for j in current['jobs']}
for job in old['jobs']:
    value=newjobs[job['id']]
    if job['id']=='JOB-0a72553fa4':
        value=dict(value);value.pop('resolution',None)
    assert value==job,'Historical task changed: '+job['id']
assert current.get('frontendPatches')==old.get('frontendPatches')
assert current.get('backendPatches')==old.get('backendPatches')
report=dict(status='PASS',pid=pid,codeFiles=2,privateConfigUnchanged=True,priorJobs=len(old['jobs']),
    originalFailurePreserved=True,patchHistoriesUnchanged=True,ordinaryProcess=True,sourceCommit='a93fe3e')
(private/'active-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
