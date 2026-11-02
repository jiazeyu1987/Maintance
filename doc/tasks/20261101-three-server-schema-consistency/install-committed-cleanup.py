"""Install only committed local release code into the idle ordinary executor."""
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import sqlite3
import subprocess
import time
import psutil

task = Path(__file__).parent
root = Path('C:/SpugHandoff/release')
work = Path('C:/SpugHandoff/schema-ops-20261101')
package = Path('C:/Users/D01021/Documents/spug-handoff-work-20261030/package')
original = Path('C:/Users/D01021/Documents/spug-handoff-minimal-20261030')
commit = '43e4d3eb6b85d4f54749d721ad4ec977102a4747'
previous = '15b2f5cc0288e045444fdea66a5083e00db55284'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def git(*args):
    return subprocess.check_output(['git','-C',str(work),*args])

def verify_bundle(folder, expected):
    data = (folder/'integrity.json').read_bytes()
    assert sha(data) == expected, 'Bundle integrity identity changed; inspect before updating'
    index = json.loads(data)
    for name, value in index['files'].items():
        relative = PurePosixPath(name)
        assert not relative.is_absolute() and '..' not in relative.parts and '\\' not in name and ':' not in name
        path = folder/name
        assert path.resolve().is_relative_to(folder.resolve()) and digest(path) == value, 'Original bundle checksum failed'
    return data, index, dict(status='PASS',files=len(index['files']),integritySha256=sha(data))

def read_state(config):
    path = Path(config['stateDir'])/'state.sqlite3'
    with sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True) as db:
        return db.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0]

def listener(config):
    sockets = [s for s in psutil.net_connections(kind='tcp')
               if s.status==psutil.CONN_LISTEN and s.laddr.port==config['port']]
    assert len(sockets)==1, 'A unique ordinary executor listener is required'
    proc = psutil.Process(sockets[0].pid)
    normalize = lambda p:str(Path(p).resolve()).casefold()
    args = proc.cmdline()
    assert any(normalize(a)==normalize(root/'source/ops/spug/release-center/intruoyi_executor.py') for a in args)
    assert any(normalize(a)==normalize(root/'executor.private.json') for a in args)
    return proc

assert git('rev-parse','HEAD').decode().strip()==commit
assert not git('status','--porcelain'), 'Fix worktree must be clean and committed'
regression = json.loads((task/'verify-regressions.json').read_text('utf-8'))
assert regression['status']=='PASS' and regression['testsRun']==531 and not regression['failures'] and not regression['errors']
for name,expected in (('real-mysql-migration-result.json','PASS'),):
    assert json.loads((task/name).read_text('utf-8'))['status']==expected
config_path = root/'executor.private.json'
config_bytes = config_path.read_bytes()
config = json.loads(config_bytes)
assert config['applicationId']=='intruoyi'
assert config['releaseWorkflow']['version']=='direct-three-server-v1'
assert config.get('requiredGxpAuditMode') in (None,'DEVELOPMENT_DISABLED')
payload = read_state(config)
state = json.loads(payload)
assert not any(j['status'] in ('running','queued','pending') for j in state['jobs']), 'Existing release is active'
old_proc = listener(config)
assert not old_proc.children(recursive=True), 'Executor still has child processes'
original_bytes, _, original_result = verify_bundle(original,'8248a204b7b87846271a0cd85ecfac53ba12e25dd830bd84da7e7afd3d060079')
print(json.dumps(dict(phase='original-bundle-verified',**original_result)),flush=True)
index_bytes, index, working_result = verify_bundle(package,'80a5cd19577262222e8704eca9bf7cc2f11a57c0351b845a097e1a7b9ab711fa')
print(json.dumps(dict(phase='working-bundle-verified',**working_result)),flush=True)
changed = git('diff','--name-only',previous,commit).decode().splitlines()
assert len(changed)==2 and all(n.startswith(('ops/spug/release-center/','ops/spug/portable/')) for n in changed)
updates = []
write_plan = []
for name in changed:
    # Portable scripts are intentionally stored at package/portable, not twice.
    relative = 'portable/README.md' if name=='ops/spug/portable/README.md' else 'source/'+name
    stable, portable = root/'source'/name, package/relative
    assert stable.exists()==portable.exists()
    old = stable.read_bytes() if stable.exists() else None
    assert old==(portable.read_bytes() if portable.exists() else None), 'Installed and working source differ'
    if old is not None:
        assert old == git('show',previous+':'+name), 'Installed file changed since previous approved commit'
    new = git('show',commit+':'+name)
    write_plan.extend([(stable,old,new),(portable,old,new)])
    updates.append(dict(file=relative,beforeSha256=sha(old) if old is not None else None,afterSha256=sha(new)))
    index['files'][relative] = sha(new)
assert config['requiredGxpAuditMode']=='DEVELOPMENT_DISABLED'
new_config = dict(config)
assert {k:v for k,v in new_config.items() if k!='requiredGxpAuditMode'} == {k:v for k,v in config.items() if k!='requiredGxpAuditMode'}
backup = root/'private'/('schema-cleanup-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
backup.mkdir(exist_ok=False)
account = subprocess.check_output(['whoami'],encoding='utf-8').strip()
subprocess.run(['icacls',str(backup),'/inheritance:r','/grant:r',account+':(OI)(CI)F',
                '*S-1-5-18:(OI)(CI)F','*S-1-5-32-544:(OI)(CI)F'],check=True,capture_output=True)
(backup/'executor.before.private.json').write_bytes(config_bytes)
(backup/'integrity.before.json').write_bytes(index_bytes)
state_path = Path(config['stateDir'])/'state.sqlite3'
with sqlite3.connect('file:'+str(state_path)+'?mode=ro',uri=True) as db, sqlite3.connect(str(backup/'state.before.sqlite3')) as saved:
    db.backup(saved)
for i,(path,old,new) in enumerate(write_plan):
    if old is not None:
        (backup/('file-'+str(i)+'.before')).write_bytes(old)
(backup/'restore-map.private.json').write_text(json.dumps([dict(path=str(p),backup='file-'+str(i)+'.before' if old is not None else None)
    for i,(p,old,_) in enumerate(write_plan)],indent=2),encoding='utf-8')
assert read_state(config)==payload and config_path.read_bytes()==config_bytes
assert listener(config).pid==old_proc.pid and not old_proc.children(recursive=True)
with (task/'execution-log.md').open('a',encoding='utf-8') as log:
    log.write('\n- GREEN: experience-preflight -> PASS（已提交构建缓存清理配套安装）。原资源包656项、工作包既有项完整校验PASS；执行器唯一空闲且无子进程，SQLite backup及私密配置/被替换文件保护备份完成。只同步提交43e4d3e的安全清理代码及测试，私密配置原字节不变；原包、原封包、凭据和历史保留，不访问服务器。\n')
old_proc.terminate()
old_proc.wait(timeout=20)
assert read_state(config)==payload
for path,old,new in write_plan:
    assert (path.read_bytes() if path.exists() else None)==old
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(new)
assert config_path.read_bytes()==config_bytes, 'Private configuration changed'
record = dict(time=datetime.now().astimezone().isoformat(),maintenanceCommit=commit,
    previousMaintenanceCommit=previous,originalVerification=original_result,previousWorkingVerification=working_result,
    updates=updates,originalBundlePreserved=True,credentialsHistoryImagesPreserved=True,
    runtimePolicy=dict(requiredGxpAuditMode='DEVELOPMENT_DISABLED',otherConfigFieldsPreserved=True),
    ordinaryScript=True,windowsServiceInstalled=False,remoteOperations=False)
receipt = 'handoff-schema-cleanup-20261101.json'
assert not (package/receipt).exists()
encoded = (json.dumps(record,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
(package/receipt).write_bytes(encoded)
index['files'][receipt] = sha(encoded)
(package/'integrity.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
new_integrity_sha = digest(package/'integrity.json')
_, after_index, after = verify_bundle(package,new_integrity_sha)
for name,expected in json.loads(index_bytes)['files'].items():
    if name not in {u['file'] for u in updates}:
        assert after_index['files'][name]==expected, 'Unrelated working bundle member changed'
assert (original/'integrity.json').read_bytes()==original_bytes
assert read_state(new_config)==payload
start = Path('C:/Users/D01021/Documents/spug-handoff-work-20261030/start-local.ps1')
with (backup/'stdout.private.log').open('wb') as out,(backup/'stderr.private.log').open('wb') as err:
    launcher = subprocess.Popen(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(start),'-SourceStopped'],
        cwd=start.parent,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
for attempt in range(60):
    sockets = [s for s in psutil.net_connections(kind='tcp')
        if s.status==psutil.CONN_LISTEN and s.laddr.port==new_config['port']]
    if sockets:
        break
    assert launcher.poll() is None, 'Ordinary startup failed; private diagnostic logs retained'
    time.sleep(.5)
new_proc = listener(new_config)
assert new_proc.pid != old_proc.pid
assert read_state(new_config)==payload, 'Release history payload changed during local code update'
assert json.loads(config_path.read_text('utf-8'))==new_config
for path,_,new in write_plan:
    assert path.read_bytes()==new
record.update(status='PASS',newExecutorPid=new_proc.pid,previousExecutorPid=old_proc.pid,
    workingVerification=after,statePayloadPreserved=True,statePayloadSha256=sha(payload.encode('utf-8')),
    jobsPreserved=len(state['jobs']),packagesPreserved=len(state['packages']),
    runtimeConfigurationReadbackPassed=True,installedCommittedFileBytesPassed=True,
    protectedBackupCreated=True,fullBusinessRegression=False)
(task/'cleanup-install-verification.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in record.items() if k!='updates'},ensure_ascii=False))
