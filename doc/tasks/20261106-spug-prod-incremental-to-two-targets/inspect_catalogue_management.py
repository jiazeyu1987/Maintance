"""Read-only exact owner/config/history pins; raw process environment stays private."""
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
from common import TASK, PRIVATE, now, write, remote
from diagnose_catalogue_504_readonly import CONTAINER, capture

sys.path.insert(0, str(PRIVATE/'test-dependencies'))
import psutil

CONFIG = Path('C:/SpugHandoff/release/executor.private.json')
SOURCE = Path('C:/SpugHandoff/release/source/ops/spug/release-center')


def pin(path):
    path = Path(path)
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def state_observation(config):
    path = Path(config['stateDir'])/'state.sqlite3'
    with sqlite3.connect(path.as_uri()+'?mode=ro', uri=True) as connection:
        raw, = connection.execute('SELECT payload FROM release_state WHERE id=1').fetchone()
    value = json.loads(raw)
    jobs = value['jobs']
    startup_changes = [j['id'] for j in jobs if j['status']=='running' or
        (j['status']=='interrupted' and (j['action'] in ('clean-artifacts','check-prerequisites','scan-artifacts') or
         (j.get('restoreVerification') and (j['action']=='verify-restore-drill' or j.get('remotePhase')=='completed'))))]
    return dict(path=str(path), payloadSha256=hashlib.sha256(raw.encode()).hexdigest(),
                jobsSha256=hashlib.sha256(json.dumps(jobs, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
                jobCount=len(jobs), startupChangedJobIds=startup_changes,
                activeJobIds=[j['id'] for j in jobs if j['status']=='running'])


def inspect():
    config = json.loads(CONFIG.read_text('utf-8-sig'))
    process = psutil.Process(35788)
    argv = process.cmdline()
    assert str(SOURCE/'intruoyi_executor.py').replace('\\','/') in [a.replace('\\','/') for a in argv]
    assert str(CONFIG).replace('\\','/') in [a.replace('\\','/') for a in argv]
    private_process = dict(pid=process.pid, createTime=process.create_time(), exe=process.exe(),
                           argv=argv, cwd=process.cwd(), environment=process.environ(), parentPid=process.ppid())
    write(PRIVATE/'catalogue-executor-process-launch.private.json', private_process)
    services = [s.name() for s in psutil.win_service_iter() if s.pid()==process.pid]
    script = '''import hashlib,json,pathlib,os
rows=[]
for p in pathlib.Path('/proc').glob('[0-9]*/cmdline'):
 try:
  argv=p.read_bytes().decode().split('\\0')
  if not any(a.endswith('/spug_bridge.py') or a.endswith('/smallapp_entry.py') for a in argv):continue
  env=dict(x.split('=',1) for x in (p.parent/'environ').read_bytes().decode().split('\\0') if '=' in x)
  row=dict(pid=int(p.parent.name),argv=argv,cwd=os.readlink(str(p.parent/'cwd')),exe=os.readlink(str(p.parent/'exe')))
  if 'RELEASE_BRIDGE_CONFIG' in env:
   path=pathlib.Path(env['RELEASE_BRIDGE_CONFIG']);raw=path.read_bytes();row['configPin']=dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
  rows.append(row)
 except (FileNotFoundError,ProcessLookupError):pass
print(json.dumps(rows))
'''
    rows=json.loads(capture('process-management', ['docker','exec','-i',CONTAINER,'python3','-B','-'], data=script.encode()))
    bridge = next(r for r in rows if any(a.endswith('/spug_bridge.py') for a in r['argv']))
    supervisor_script = '''import configparser,hashlib,json,pathlib
p=pathlib.Path('/proc/2124/status');values=dict(line.split(':',1) for line in p.read_text().splitlines() if ':' in line)
parent=int(values['PPid'].strip());args=(pathlib.Path('/proc')/str(parent)/'cmdline').read_bytes().decode().split('\\0')
path=pathlib.Path('/etc/supervisord.conf');raw=path.read_bytes();config=configparser.RawConfigParser();config.read_string(raw.decode())
rows=[dict(name=s,command=config.get(s,'command'),autorestart=config.get(s,'autorestart',fallback='unexpected'),exitcodes=config.get(s,'exitcodes',fallback='0')) for s in config.sections() if s.startswith('program:') and 'spug_bridge.py' in config.get(s,'command',fallback='')]
print(json.dumps(dict(parentPid=parent,parentArgv=args,programs=rows,configPin=dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()),supervisorctlConfigured=config.has_section('supervisorctl'))))
'''
    supervisor=json.loads(capture('supervisor-management',['docker','exec','-i',CONTAINER,'python3','-B','-'],data=supervisor_script.encode()))
    entry = next(r for r in rows if any(a.endswith('/smallapp_entry.py') for a in r['argv']))
    source = remote('172.30.30.57', "import subprocess,json\nprint(json.dumps(dict(pid=int(subprocess.check_output(['systemctl','show','spug-intruoyi-source-57-20261105.service','--property=MainPID','--value']).decode().strip()))))\n", timeout=25)
    result = dict(observedAt=now(), executor=dict(pid=process.pid, createTime=process.create_time(),
                  exe=process.exe(), script=str(SOURCE/'intruoyi_executor.py'), configPin=pin(CONFIG),
                  launchRecordPin=pin(PRIVATE/'catalogue-executor-process-launch.private.json'),
                  services=services, childPids=[p.pid for p in process.children()], cwd=process.cwd()),
                  bridge=dict(bridge, containerId=CONTAINER, supervisor=supervisor),
                  protected=dict(smallappEntryPid=entry['pid'], source57ServicePid=source['pid']),
                  history=state_observation(config), runtimeWrites=0)
    write(TASK/'catalogue-identity-process-management.json', result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__=='__main__':
    inspect()
