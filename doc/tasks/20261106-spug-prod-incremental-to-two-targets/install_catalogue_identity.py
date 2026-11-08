"""Prepare by default; --apply upgrades only exact idle release components."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import urllib.request

from common import TASK, PRIVATE, now, write, remote
from diagnose_catalogue_504_readonly import CONTAINER
from inspect_catalogue_management import CONFIG, SOURCE, pin, state_observation

sys.path.insert(0, str(PRIVATE/'test-dependencies'))
import psutil

BRIDGE = Path('C:/Spug/runtime/ops/spug/release-center')
BRIDGE_CONFIG = '/var/lib/intruoyi-spug/release-center-bridge.private.json'
EXECUTOR_FILES = ('executor.py', 'package_catalog.py', 'package_presence.py')
BRIDGE_FILES = ('application_registry.py', 'release_http.py')


def run(args, *, data=None, timeout=40, cwd=None):
    result = subprocess.run(args, input=data, capture_output=True, timeout=timeout, cwd=cwd)
    if result.returncode:
        raw = result.stdout + result.stderr
        (PRIVATE/('catalogue-install-error-'+hashlib.sha256(raw).hexdigest()[:12]+'.private.log')).write_bytes(raw)
        raise RuntimeError('CATALOGUE_INSTALL_COMMAND_FAILED_'+str(result.returncode))
    return result.stdout


def docker(*args, data=None):
    return run(['docker', *args], data=data)


def source_pid():
    code = "import subprocess,json\nprint(json.dumps(dict(pid=int(subprocess.check_output(['systemctl','show','spug-intruoyi-source-57-20261105.service','--property=MainPID','--value']).decode().strip()))))\n"
    value = remote('172.30.30.57', code, timeout=25)['pid']
    assert value > 0
    return value


def container_observation():
    value = json.loads(docker('inspect', CONTAINER))[0]
    assert value['Id'] == CONTAINER
    assert value['NetworkSettings']['Ports']['80/tcp'] == [{'HostIp':'127.0.0.1','HostPort':'18080'}]
    mount = next(x for x in value['Mounts'] if x['Destination']=='/opt/intruoyi-spug')
    assert Path(mount['Source']).resolve() == BRIDGE.parent.resolve()
    script = '''import configparser,hashlib,json,os,pathlib
def pin(path):
 raw=pathlib.Path(path).read_bytes();return dict(path=path,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
rows=[]
for p in pathlib.Path('/proc').glob('[0-9]*/cmdline'):
 try:
  argv=p.read_bytes().decode().rstrip('\\0').split('\\0')
  if argv not in (['python3','-B','/opt/intruoyi-spug/release-center/spug_bridge.py'],['python3','-B','/opt/intruoyi-spug/smallapp_entry.py']):continue
  env=dict(v.split('=',1) for v in (p.parent/'environ').read_bytes().decode().split('\\0') if '=' in v)
  status=dict(v.split(':',1) for v in (p.parent/'status').read_text().splitlines() if ':' in v)
  rows.append(dict(pid=int(p.parent.name),argv=argv,parentPid=int(status['PPid']),startTime=(p.parent/'stat').read_text().split()[21],configPath=env.get('RELEASE_BRIDGE_CONFIG')))
 except (FileNotFoundError,ProcessLookupError):pass
bridge=[r for r in rows if r['argv'][-1].endswith('/spug_bridge.py')];entry=[r for r in rows if r['argv'][-1].endswith('/smallapp_entry.py')]
assert len(bridge)==len(entry)==1
assert bridge[0]['parentPid']==1 and bridge[0]['configPath']=='/var/lib/intruoyi-spug/release-center-bridge.private.json'
assert 'supervisord' in pathlib.Path('/proc/1/cmdline').read_bytes().decode()
c=configparser.RawConfigParser();c.read('/etc/supervisord.conf')
section='program:release-center-bridge'
assert c.get(section,'command')=='python3 -B /opt/intruoyi-spug/release-center/spug_bridge.py'
assert c.get(section,'autorestart')=='unexpected' and c.get(section,'exitcodes',fallback='0')=='0'
print(json.dumps(dict(bridge=bridge[0],smallappEntryPid=entry[0]['pid'],configPin=pin(bridge[0]['configPath']),supervisorPin=pin('/etc/supervisord.conf'),nginxPin=pin('/etc/nginx/nginx.conf'),locationsPin=pin('/opt/intruoyi-spug/release-center/locations.conf'))))
'''
    observed = json.loads(docker('exec','-i',CONTAINER,'python3','-B','-',data=script.encode()))
    ids = docker('ps','-aq').decode().split()
    unrelated = []
    if ids:
        for row in json.loads(docker('inspect',*ids)):
            ports = row['HostConfig'].get('PortBindings') or {}
            if any(p['HostPort']=='18081' for values in ports.values() for p in (values or [])):
                assert row['Id'] != CONTAINER
                unrelated.append(dict(id=row['Id'],state=row['State']['Status'],startedAt=row['State']['StartedAt']))
    observed['unrelated18081'] = unrelated
    return observed


def exact_process(launch):
    process = psutil.Process(launch['pid'])
    assert process.create_time() == launch['createTime']
    assert process.cmdline() == launch['argv'] and process.exe() == launch['exe']
    assert process.cwd() == launch['cwd']
    assert not [s for s in psutil.win_service_iter() if s.pid()==process.pid], 'UNEXPECTED_SERVICE_MANAGER'
    assert all(p.name().lower()=='conhost.exe' for p in process.children()), 'ACTIVE_EXECUTOR_CHILD_PROCESS'
    return process


def http(config, route):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request('http://127.0.0.1:'+str(config['port'])+route,
                                     headers={'X-Release-Key':config['bridgeKey']})
    with opener.open(request, timeout=4) as response:
        raw = response.read(1024*1024+1)
        assert len(raw)<=1024*1024
        return response.status, json.loads(raw)


def committed_inputs(root, commit):
    assert root.resolve().is_relative_to(PRIVATE.resolve()), 'DEDICATED_TASK_WORKTREE_REQUIRED'
    assert root.resolve() != TASK.parents[2].resolve()
    assert run(['git','rev-parse','HEAD'],cwd=root).decode().strip() == commit
    assert not run(['git','status','--porcelain','--untracked-files=all'],cwd=root).strip()
    inputs = {}
    for name in (*EXECUTOR_FILES,*BRIDGE_FILES):
        path = root/'ops/spug/release-center'/name
        raw = path.read_bytes()
        ast.parse(raw.decode('utf-8'), filename=name)
        committed = run(['git','show',commit+':ops/spug/release-center/'+name],cwd=root)
        assert raw.replace(b'\r\n',b'\n') == committed.replace(b'\r\n',b'\n')
        inputs[name] = dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    return inputs


def prepare(root, commit):
    report_path = TASK/('catalogue-identity-install-plan-'+commit[:7]+'.json')
    assert not report_path.exists(), 'EXISTING_PLAN_MUST_NOT_BE_OVERWRITTEN'
    source_pins = committed_inputs(root, commit)
    launch_path = PRIVATE/'catalogue-executor-process-launch.private.json'
    launch = json.loads(launch_path.read_text('utf-8'))
    process = exact_process(launch)
    config = json.loads(CONFIG.read_text('utf-8-sig'))
    assert config['applicationId']=='intruoyi' and config['port']==18112
    history = state_observation(config)
    assert history['jobCount']==309 and not history['activeJobIds'] and not history['startupChangedJobIds']
    observed = container_observation()
    backup = PRIVATE/('catalogue-before-'+commit[:7])
    backup.mkdir(exist_ok=False)
    originals = {}
    for component, base, names in [('executor',SOURCE,EXECUTOR_FILES),('bridge',BRIDGE,(*BRIDGE_FILES,'spug_bridge.py'))]:
        for name in names:
            key = component+'/'+name
            path = base/name
            originals[key] = pin(path) if path.exists() else None
            if path.exists():
                target = backup/component/name
                target.parent.mkdir(exist_ok=True)
                target.write_bytes(path.read_bytes())
    (backup/'executor.private.json').write_bytes(CONFIG.read_bytes())
    bridge_raw = docker('exec',CONTAINER,'cat',BRIDGE_CONFIG)
    (backup/'bridge.private.json').write_bytes(bridge_raw)
    with sqlite3.connect(Path(history['path']).as_uri()+'?mode=ro',uri=True) as src:
        with sqlite3.connect(backup/'state.sqlite3') as target:
            src.backup(target)
    assert state_observation(config)==history
    # Use the actual runtime interpreter/import closure without constructing the
    # service or loading state. The candidate executor adds no third-party import.
    check = "import executor,package_catalog,package_presence,intruoyi_executor; assert callable(executor.create_server); print('IMPORT_CLOSURE_PASS')"
    assert run([launch['exe'],'-X','utf8','-B','-c',check],cwd=SOURCE).strip()==b'IMPORT_CLOSURE_PASS'
    for name in ('package_catalog.py','package_presence.py'):
        assert (SOURCE/name).read_bytes().replace(b'\r\n',b'\n') == (root/'ops/spug/release-center'/name).read_bytes().replace(b'\r\n',b'\n')
    plan = dict(schemaVersion='CatalogueIdentityInstallPlan/v1', status='PREPARED', observedAt=now(),
                sourceCommit=commit, buildWorktree=str(root), sourcePins=source_pins,
                originalFiles=originals, backupRoot=str(backup), history=history,
                historyBackupPin=pin(backup/'state.sqlite3'), executorConfigPin=pin(CONFIG),
                launchRecordPin=pin(launch_path), previousExecutorPid=process.pid,
                container=observed, protected=dict(smallappEntryPid=observed['smallappEntryPid'],
                source57ServicePid=source_pid(), unrelated18081=observed['unrelated18081']),
                runtimeWrites=0)
    write(report_path,plan)
    return plan


def apply(root, commit):
    plan = json.loads((TASK/('catalogue-identity-install-plan-'+commit[:7]+'.json')).read_text('utf-8'))
    assert plan['schemaVersion']=='CatalogueIdentityInstallPlan/v1' and plan['status']=='PREPARED'
    assert Path(plan['buildWorktree']).resolve()==root.resolve() and plan['sourceCommit']==commit
    assert committed_inputs(root,commit)==plan['sourcePins']
    assert pin(CONFIG)==plan['executorConfigPin']
    assert pin(plan['launchRecordPin']['path'])==plan['launchRecordPin']
    launch = json.loads(Path(plan['launchRecordPin']['path']).read_text('utf-8'))
    process=exact_process(launch)
    config=json.loads(CONFIG.read_text('utf-8-sig'))
    assert state_observation(config)==plan['history']
    assert container_observation()==plan['container']
    assert source_pid()==plan['protected']['source57ServicePid']
    for key, expected in plan['originalFiles'].items():
        part,name=key.split('/')
        path=(SOURCE if part=='executor' else BRIDGE)/name
        assert (pin(path) if path.exists() else None)==expected
    report=dict(schemaVersion='CatalogueIdentityInstallation/v1',status='STARTED',observedAt=now(),
                sourceCommit=commit,buildWorktree=str(root),protectedBefore=plan['protected'])
    report_path=TASK/'catalogue-identity-installation.json'
    assert not report_path.exists(), 'INSTALLATION_REPORT_ALREADY_EXISTS'
    write(report_path,report)
    try:
        process.terminate()
        process.wait(timeout=15)
        assert state_observation(config)==plan['history'], 'HISTORY_CHANGED_DURING_STOP'
        # No function splicing and no private template overwrite. Whole executor
        # bytes come from the committed worktree, with existing catalogue retained.
        for name in EXECUTOR_FILES:
            (SOURCE/name).write_bytes((root/'ops/spug/release-center'/name).read_bytes())
        output=Path(plan['backupRoot'])/'new-executor.stdout.log'
        errors=Path(plan['backupRoot'])/'new-executor.stderr.log'
        with output.open('ab') as stdout, errors.open('ab') as stderr:
            new=subprocess.Popen(launch['argv'],cwd=launch['cwd'],env=launch['environment'],
                stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,
                creationflags=subprocess.CREATE_NO_WINDOW)
        deadline=time.monotonic()+20
        while True:
            assert new.poll() is None, 'NEW_EXECUTOR_EXITED'
            try:
                status,identity=http(config,'/identity')
                assert status==200 and identity['schemaVersion']=='ReleaseExecutorIdentity/v1'
                assert identity['application']['id']=='intruoyi'
                break
            except (OSError,urllib.error.URLError):
                if time.monotonic()>=deadline:raise
                time.sleep(.2)
        new_process=psutil.Process(new.pid)
        assert new.pid != process.pid and new_process.create_time() > launch['createTime']
        assert new_process.exe()==launch['exe'] and new_process.cmdline()==launch['argv']
        assert new_process.cwd()==launch['cwd'], 'NEW_EXECUTOR_LAUNCH_IDENTITY_DIFFERS'
        assert all({k:v for k,v in pin(SOURCE/name).items() if k!='path'}==plan['sourcePins'][name] for name in EXECUTOR_FILES), 'EXECUTOR_COMMITTED_FILE_PIN_MISMATCH'
        report['executor']=dict(runtime=str(SOURCE),actualPid=new.pid,previousPid=process.pid,
            createTime=new_process.create_time(),exe=new_process.exe(),cwd=new_process.cwd(),
            argvSha256=hashlib.sha256(json.dumps(new_process.cmdline(),ensure_ascii=False).encode()).hexdigest(),configPin=pin(CONFIG),
            filePins={name:{k:v for k,v in pin(SOURCE/name).items() if k!='path'} for name in EXECUTOR_FILES})
        write(report_path,report)
        assert state_observation(config)==plan['history'], 'HISTORY_CHANGED_AFTER_RELOAD'
        for name in BRIDGE_FILES:
            (BRIDGE/name).write_bytes((root/'ops/spug/release-center'/name).read_bytes())
        # Existing supervisor has no supervisorctl section. Its proved policy
        # restarts unexpected exits; target only the original exact child PID.
        old=plan['container']['bridge']
        kill_script='''import json,os,pathlib,signal,sys
expected=json.load(sys.stdin);p=pathlib.Path('/proc')/str(expected['pid'])
assert (p/'cmdline').read_bytes().decode().rstrip('\\0').split('\\0')==expected['argv']
assert (p/'stat').read_text().split()[21]==expected['startTime']
status=dict(x.split(':',1) for x in (p/'status').read_text().splitlines() if ':' in x)
assert int(status['PPid'])==1
os.kill(expected['pid'],signal.SIGTERM)
print('EXACT_BRIDGE_SIGTERM_SENT')
'''
        assert docker('exec','-i',CONTAINER,'python3','-B','-c',kill_script,data=json.dumps(old).encode()).strip()==b'EXACT_BRIDGE_SIGTERM_SENT'
        deadline=time.monotonic()+20
        while True:
            try:
                current=container_observation()
                if current['bridge']['pid']!=old['pid']:break
            except (RuntimeError,AssertionError):
                if time.monotonic()>=deadline:raise
            assert time.monotonic()<deadline, 'BRIDGE_RESTART_TIMEOUT'
            time.sleep(.3)
        assert current['configPin']==plan['container']['configPin']
        for name in ('supervisorPin','nginxPin','locationsPin','smallappEntryPid','unrelated18081'):
            assert current[name]==plan['container'][name], 'PROTECTED_SPUG_COMPONENT_CHANGED_'+name
        # Execute the actual new registry from the same container; keep keys private.
        probe='''import json,pathlib,sys,time
sys.path.insert(0,'/opt/intruoyi-spug/release-center')
from application_registry import ApplicationRegistry
c=json.loads(pathlib.Path('/var/lib/intruoyi-spug/release-center-bridge.private.json').read_text())
r=ApplicationRegistry(c);app,path=r.resolve('/applications/intruoyi/package-catalog','GET');t=time.monotonic()
status,raw=r.request(app,path,'GET',None,'catalogue-install-readonly');value=json.loads(raw)
print(json.dumps(dict(status=status,schemaVersion=value.get('schemaVersion'),items=len(value.get('items',[])),refreshing=value.get('refreshing'),elapsedSeconds=round(time.monotonic()-t,3),responseBytes=len(raw))))
'''
        validation=json.loads(docker('exec','-i',CONTAINER,'python3','-B','-',data=probe.encode()))
        assert validation['status']==200 and validation['schemaVersion']=='PackageCatalog/v1'
        assert all({k:v for k,v in pin(BRIDGE/name).items() if k!='path'}==plan['sourcePins'][name] for name in BRIDGE_FILES), 'BRIDGE_COMMITTED_FILE_PIN_MISMATCH'
        report['bridge']=dict(runtime=str(BRIDGE),containerId=CONTAINER,actualPid=current['bridge']['pid'],
            previousPid=old['pid'],startTime=current['bridge']['startTime'],configPin=current['configPin'],supervisorProgram='release-center-bridge',
            filePins={name:{k:v for k,v in pin(BRIDGE/name).items() if k!='path'} for name in (*BRIDGE_FILES,'spug_bridge.py')})
        after=state_observation(config)
        protected=dict(smallappEntryPid=current['smallappEntryPid'],source57ServicePid=source_pid(),unrelated18081=current['unrelated18081'])
        report.update(protectedAfter=protected,history=dict(before=plan['history'],after=after,backupPin=plan['historyBackupPin']),
            allOriginalJobsPreserved=after==plan['history'],existingConfigurationPreserved=pin(CONFIG)==plan['executorConfigPin'] and current['configPin']==plan['container']['configPin'],
            unrelated18081Preserved=protected['unrelated18081']==plan['protected']['unrelated18081'],
            originalSourceControlPidPreserved=protected['source57ServicePid']==plan['protected']['source57ServicePid'],
            smallappEntryPidPreserved=protected['smallappEntryPid']==plan['protected']['smallappEntryPid'],
            validation=validation,realBrowserVerified=False)
        assert all(report[key] for key in ('allOriginalJobsPreserved','existingConfigurationPreserved','unrelated18081Preserved','originalSourceControlPidPreserved','smallappEntryPidPreserved'))
        report.update(status='PASS',observedAt=now())
        write(report_path,report)
        return report
    except BaseException as exc:
        report.update(status='FAIL',observedAt=now(),errorType=type(exc).__name__,error=str(exc) if isinstance(exc,AssertionError) else 'INSPECT_PRIVATE_LOGS')
        write(report_path,report)
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--commit',required=True)
    parser.add_argument('--worktree',type=Path,required=True)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    value=apply(args.worktree,args.commit) if args.apply else prepare(args.worktree,args.commit)
    print(json.dumps({key:value[key] for key in ('schemaVersion','status','sourceCommit','observedAt')}))
