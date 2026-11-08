"""Read-only current catalogue processes/files/history; no service construction."""
import hashlib
import json
from pathlib import Path
import sqlite3

from common import now


def require_original_jobs(original, current):
    assert isinstance(original, list) and isinstance(current, list)
    old = {row['id']: row for row in original}
    live = {row['id']: row for row in current}
    assert len(old) == len(original) and len(live) == len(current), 'CATALOGUE_JOB_IDS_DUPLICATED'
    assert old == live, 'CATALOGUE_ORIGINAL_JOBS_CHANGED'


def jobs(path):
    with sqlite3.connect(Path(path).as_uri() + '?mode=ro', uri=True) as connection:
        raw, = connection.execute('SELECT payload FROM release_state WHERE id=1').fetchone()
    return json.loads(raw)['jobs']


def check_files(root, pins, allowed):
    assert set(pins) == set(allowed), 'CATALOGUE_FILE_SET_CHANGED'
    for name, expected in pins.items():
        path = root / name
        assert path.resolve().parent == root.resolve() and not path.is_symlink(), 'CATALOGUE_FILE_PATH_CHANGED'
        raw = path.read_bytes()
        assert expected == dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()), 'CATALOGUE_RUNTIME_FILE_CHANGED'


def require_current_protected_processes(installed, source_installation, actual):
    assert installed['protectedBefore'] == installed['protectedAfter'], 'CATALOGUE_HISTORICAL_PROTECTION_CHANGED'
    assert source_installation['schemaVersion'] == 'AutomaticSourceControlUpgrade/v1' and source_installation['status'] == 'PASS'
    source = source_installation['controllers'][0]
    assert source['service'] == 'spug-intruoyi-source-57-20261105.service'
    expected = dict(installed['protectedAfter'])
    assert source['previousPid'] == expected['source57ServicePid'], 'CATALOGUE_SOURCE_PREDECESSOR_CHANGED'
    assert type(source['pid']) is int and source['pid'] > 0 and source['pid'] != source['previousPid']
    expected['source57ServicePid'] = source['pid']
    assert actual == expected, 'CATALOGUE_PROTECTED_PROCESS_CHANGED'


def verify_current_catalogue(installed, source_installation):
    # These shared observation functions only read actual OS/config/SQLite/HTTP state.
    # Installer prepare/apply are never called here.
    from install_catalogue_identity import (BRIDGE, CONFIG, SOURCE, CONTAINER, psutil,
                                            pin, state_observation, container_observation, source_pid, http, docker)
    assert installed['schemaVersion'] == 'CatalogueIdentityInstallation/v1' and installed['status'] == 'PASS'
    executor, bridge = installed['executor'], installed['bridge']
    assert Path(executor['runtime']).resolve() == SOURCE.resolve()
    assert Path(bridge['runtime']).resolve() == BRIDGE.resolve() and bridge['containerId'] == CONTAINER
    assert bridge['supervisorProgram'] == 'release-center-bridge'
    check_files(SOURCE, executor['filePins'], ('executor.py', 'package_catalog.py', 'package_presence.py'))
    check_files(BRIDGE, bridge['filePins'], ('application_registry.py', 'release_http.py', 'spug_bridge.py'))
    assert pin(CONFIG) == executor['configPin'], 'CATALOGUE_EXECUTOR_CONFIGURATION_CHANGED'
    process = psutil.Process(executor['actualPid'])
    assert process.create_time() == executor['createTime'] and process.exe() == executor['exe'], 'CATALOGUE_EXECUTOR_PROCESS_REUSED'
    assert process.cwd() == executor['cwd']
    assert hashlib.sha256(json.dumps(process.cmdline(), ensure_ascii=False).encode('utf-8')).hexdigest() == executor['argvSha256']
    argv = [value.replace('\\', '/') for value in process.cmdline()]
    assert str(SOURCE / 'intruoyi_executor.py').replace('\\', '/') in argv
    assert str(CONFIG).replace('\\', '/') in argv and process.pid != executor['previousPid']
    actual = container_observation()
    assert actual['bridge']['pid'] == bridge['actualPid'] != bridge['previousPid'], 'CATALOGUE_BRIDGE_PROCESS_CHANGED'
    assert actual['bridge']['startTime'] == bridge['startTime'], 'CATALOGUE_BRIDGE_PID_REUSED'
    assert actual['configPin'] == bridge['configPin'], 'CATALOGUE_BRIDGE_CONFIGURATION_CHANGED'
    protected = dict(smallappEntryPid=actual['smallappEntryPid'], source57ServicePid=source_pid(), unrelated18081=actual['unrelated18081'])
    require_current_protected_processes(installed, source_installation, protected)
    config = json.loads(CONFIG.read_text(encoding='utf-8-sig'))
    assert config['applicationId'] == 'intruoyi' and config['port'] == 18112
    current = state_observation(config)
    backup = installed['history']['backupPin']
    assert pin(backup['path']) == backup, 'CATALOGUE_HISTORY_BACKUP_CHANGED'
    require_original_jobs(jobs(backup['path']), jobs(current['path']))
    assert current['jobsSha256'] == installed['history']['before']['jobsSha256'] == installed['history']['after']['jobsSha256']
    assert current['jobCount'] == installed['history']['before']['jobCount'] == installed['history']['after']['jobCount']
    assert not current['activeJobIds'] and not current['startupChangedJobIds'], 'CATALOGUE_JOB_NOT_IDLE'
    status, identity = http(config, '/identity')
    assert status == 200 and identity['schemaVersion'] == 'ReleaseExecutorIdentity/v1' and identity['application']['id'] == 'intruoyi'
    probe = '''import json,pathlib,sys
sys.path.insert(0,'/opt/intruoyi-spug/release-center')
from application_registry import ApplicationRegistry
configuration=json.loads(pathlib.Path('/var/lib/intruoyi-spug/release-center-bridge.private.json').read_text())
registry=ApplicationRegistry(configuration)
application,path=registry.resolve('/applications/intruoyi/package-catalog','GET')
status,raw=registry.request(application,path,'GET',None,'task-closeout-readonly')
value=json.loads(raw)
assert status==200 and value['schemaVersion']=='PackageCatalog/v1'
print(json.dumps(dict(status='PASS',httpStatus=status,itemCount=len(value['items']))))
'''
    catalogue = json.loads(docker('exec', '-i', CONTAINER, 'python3', '-B', '-', data=probe.encode('utf-8')))
    assert state_observation(config)['jobsSha256'] == current['jobsSha256'], 'CATALOGUE_READ_CHANGED_JOBS'
    return dict(status='PASS', observedAt=now(), sourceCommit=installed['sourceCommit'], executorPid=process.pid,
                bridgePid=bridge['actualPid'], runtimeFilesAndProcessesVerified=True, originalJobCount=current['jobCount'],
                allOriginalJobsPreserved=True, existingConfigurationPreserved=True, protectedProcessesPreserved=True,
                sourceControlSuccessorVerified=True, sourceControlPreviousPid=installed['protectedAfter']['source57ServicePid'],
                sourceControlCurrentPid=protected['source57ServicePid'],
                executorIdentityHttp=200, catalogueHttp=catalogue['httpStatus'], realBrowserVerified=False, runtimeWrites=False)
