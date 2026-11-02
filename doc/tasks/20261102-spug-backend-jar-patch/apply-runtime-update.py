"""Idle ordinary-process update; verify private configuration and history unchanged."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import urllib.request
import psutil

phase=sys.argv[1]
root=Path('C:/SpugHandoff/release')
private=root/'private/backend-jar-patch-20261102'
live=root/'source/ops/spug/release-center'
candidate=private/'candidate-source/ops/spug/release-center'
plan=json.loads((private/'code-update-plan.json').read_text('utf-8'))
config_path=root/'executor.private.json'
config=json.loads(config_path.read_text('utf-8'))

def require(ok,message):
    if not ok:raise SystemExit(message)

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None

def state():
    with sqlite3.connect('file:'+str(root/'state/state.sqlite3').replace('\\','/')+'?mode=ro',uri=True) as connection:
        value=json.loads(connection.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
    require(not any(j['status'] in ('running','queued') for j in value['jobs']),'Active job blocks update')
    return dict(sha256=hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=True).encode()).hexdigest(),
                jobs=len(value['jobs']),packages=len(value['packages']),patches=len(value.get('frontendPatches',[])))

def owners():return set(c.pid for c in psutil.net_connections(kind='tcp') if c.status=='LISTEN' and c.laddr.port==config['port'])

def snapshot():
    request=urllib.request.Request('http://127.0.0.1:'+str(config['port'])+'/state',headers={'X-Release-Key':config['bridgeKey']})
    with urllib.request.urlopen(request,timeout=20) as response:value=json.load(response)
    require(not any(j['status'] in ('running','queued') for j in value['jobs']),'Active live job blocks update')
    return value

def identity():
    pids=owners();require(len(pids)==1,'Expected exactly one executor listener')
    process=psutil.Process(pids.pop());command=[a.replace('\\','/') for a in process.cmdline()]
    require(process.name().lower()=='python.exe' and (live/'intruoyi_executor.py').as_posix() in command
            and config_path.as_posix() in command,'Unexpected listener identity')
    return process

if phase=='preflight':
    snapshot();process=identity()
    for row in plan:
        require(sha(live/row['name'])==row['beforeSha256'],'Live code changed: '+row['name'])
        require(sha(candidate/row['name'])==row['afterSha256'],'Candidate changed: '+row['name'])
    evidence=dict(pid=process.pid,processCreated=process.create_time(),python=process.exe(),configSha256=sha(config_path),state=state())
    (private/'before.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    print(json.dumps(dict(status='idle',pid=process.pid,**evidence['state'])))
elif phase=='stop':
    before=json.loads((private/'before.json').read_text('utf-8'))
    snapshot();process=identity()
    require(process.pid==before['pid'] and process.create_time()==before['processCreated'],'Process changed')
    require(sha(config_path)==before['configSha256'] and state()==before['state'],'History/config changed')
    process.terminate();process.wait(timeout=15)
    require(not owners(),'Listener remains after stop')
    print(json.dumps(dict(status='stopped',pid=process.pid,ordinaryProcess=True)))
elif phase=='install':
    before=json.loads((private/'before.json').read_text('utf-8'))
    require(not owners(),'Executor must stop before mutation')
    require(not(psutil.pid_exists(before['pid']) and psutil.Process(before['pid']).create_time()==before['processCreated']),'Reviewed executor remains active')
    require(sha(config_path)==before['configSha256'] and state()==before['state'],'Private state/config changed')
    for row in plan:
        require(sha(live/row['name'])==row['beforeSha256'] and sha(candidate/row['name'])==row['afterSha256'],'Code changed: '+row['name'])
    backup=private/'original-code';backup.mkdir(exist_ok=False)
    # Private backups stay outside Git; never print their contents.
    shutil.copyfile(config_path,private/'executor-before.private.json')
    with sqlite3.connect(root/'state/state.sqlite3') as original,sqlite3.connect(private/'state-before.private.sqlite3') as copied:original.backup(copied)
    for row in plan:
        path=live/row['name']
        if path.exists():
            target=backup/row['name'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
    for row in plan:
        path=live/row['name'];path.parent.mkdir(parents=True,exist_ok=True)
        temporary=path.with_suffix(path.suffix+'.backend-update');shutil.copyfile(candidate/row['name'],temporary);os.replace(temporary,path)
        require(sha(path)==row['afterSha256'],'Installed SHA mismatch: '+row['name'])
    print(json.dumps(dict(status='installed',files=len(plan),configUnchanged=True,historyUnchanged=True)))
elif phase=='verify':
    value=snapshot();identity()
    before=json.loads((private/'before.json').read_text('utf-8'))
    require(sha(config_path)==before['configSha256'] and state()==before['state'],'Private state/config changed after restart')
    require(all(sha(live/r['name'])==r['afterSha256'] for r in plan),'Installed source drift')
    require(value['application']['capabilities']['backendPatch'] is True,'Backend patch capability absent')
    with urllib.request.urlopen('http://127.0.0.1:18081/',timeout=15) as response:require(response.status==200,'Spug HTTP failed')
    result=dict(status='passed',codeFiles=len(plan),privateConfigUnchanged=True,historyUnchanged=True,
                state=state(),executorPort=config['port'],spugHttpStatus=200,servicesInstalled=0,remoteOperations=0)
    (private/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))
else:raise SystemExit('Unknown phase')
