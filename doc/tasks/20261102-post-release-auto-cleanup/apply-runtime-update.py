"""Code-only local executor update with immutable config/history verification."""
from pathlib import Path
import hashlib
import json
import shutil
import sqlite3
import sys
import urllib.request
import psutil

phase=sys.argv[1]
root=Path('C:/SpugHandoff/release')
private=root/'private/post-release-cleanup-20261102'
live=root/'source/ops/spug/release-center'
candidate=private/'candidate-source-v3/ops/spug/release-center'
plan=json.loads((private/'code-update-plan.json').read_text('utf-8'))
config_path=root/'executor.private.json'
config=json.loads(config_path.read_text('utf-8'))
def require(ok, message):
    if not ok: raise SystemExit(message)
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
def state():
    with sqlite3.connect('file:'+str(root/'state/state.sqlite3').replace('\\','/')+'?mode=ro',uri=True) as connection:
        value=json.loads(connection.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
    require(not any(j['status'] in ('running','queued') for j in value['jobs']), 'Active job blocks local code update')
    return dict(sha256=hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=True).encode()).hexdigest(),
                jobs=len(value['jobs']),packages=len(value['packages']),patches=len(value.get('frontendPatches',[])))
def listening():
    return [c.pid for c in psutil.net_connections(kind='tcp') if c.status=='LISTEN' and c.laddr.port==config['port']]
def authenticated_snapshot():
    request=urllib.request.Request('http://127.0.0.1:'+str(config['port'])+'/state',headers={'X-Release-Key':config['bridgeKey']})
    with urllib.request.urlopen(request,timeout=20) as response: value=json.load(response)
    require(not any(j['status'] in ('running','queued') for j in value['jobs']), 'Live active job blocks local code update')
    return value

if phase=='preflight':
    authenticated_snapshot()
    owners=set(listening());require(len(owners)==1,'Expected exactly one local executor')
    pid=owners.pop();process=psutil.Process(pid);command=[a.replace('\\','/') for a in process.cmdline()]
    require(process.name().lower()=='python.exe' and str(live/'intruoyi_executor.py').replace('\\','/') in command
            and str(config_path).replace('\\','/') in command,'Listener is not this stable executor')
    for row in plan:
        require(sha(live/row['name'])==row['beforeSha256'],'Live code changed before review: '+row['name'])
        require(sha(candidate/row['name'])==row['afterSha256'],'Candidate code changed: '+row['name'])
    evidence=dict(pid=pid,processCreated=process.create_time(),configSha256=sha(config_path),state=state())
    (private/'before.json').write_text(json.dumps(evidence,indent=2),'utf-8')
    print(json.dumps(dict(status='idle',pid=pid,**evidence['state'])))
elif phase=='install':
    before=json.loads((private/'before.json').read_text('utf-8'))
    require(not listening(),'Executor must stop before code mutation')
    require(not (psutil.pid_exists(before['pid']) and psutil.Process(before['pid']).create_time()==before['processCreated']),
            'Reviewed executor remains active')
    require(sha(config_path)==before['configSha256'] and state()==before['state'],'Private state/config changed')
    backup=private/'original-code';backup.mkdir(exist_ok=False)
    for row in plan:
        path=live/row['name'];require(sha(path)==row['beforeSha256'],'Code changed: '+row['name'])
        if path.exists():shutil.copyfile(path,backup/row['name'])
    for row in plan:
        path=live/row['name'];shutil.copyfile(candidate/row['name'],path)
        require(sha(path)==row['afterSha256'],'Installed code SHA mismatch: '+row['name'])
    print(json.dumps(dict(status='installed',files=len(plan),privateConfigUnchanged=True,historyUnchanged=True)))
elif phase=='verify':
    authenticated_snapshot()
    before=json.loads((private/'before.json').read_text('utf-8'))
    require(sha(config_path)==before['configSha256'] and state()==before['state'],'Private state/config changed after restart')
    require(all(sha(live/r['name'])==r['afterSha256'] for r in plan),'Installed code drift')
    require(len(set(listening()))==1,'Executor listener count changed')
    with urllib.request.urlopen('http://127.0.0.1:18081/',timeout=15) as response:require(response.status==200,'Spug page failed')
    result=dict(status='passed',codeFiles=len(plan),configUnchanged=True,historyUnchanged=True,
                state=state(),executorPort=config['port'],spugHttpStatus=200,servicesInstalled=0,remoteMutations=0)
    (private/'verification.json').write_text(json.dumps(result,indent=2),'utf-8')
    print(json.dumps(result))
else: raise SystemExit('Unknown phase')
