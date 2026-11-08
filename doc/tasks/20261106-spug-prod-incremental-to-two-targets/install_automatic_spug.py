"""Deploy committed automatic-entry resources to the exact 18080 Spug only."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from common import TASK, PRIVATE, now, write

DOCKER = 'C:/Users/D01021/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe'
CONTAINER = 'f615a60c76f46e4f6ae20ea6298f737fb9786684ce941fcc15763654461265bf'
RUNTIME = Path('C:/Spug/runtime/ops/spug')
FILES = ['smallapp_entry.py', 'smallapp_adapter.py', 'smallapp-entry.locations.conf',
         *['smallapp-ui/' + name for name in ('app.js', 'simple.js', 'index.html', 'simple.css',
                                             'embedded.js', 'embedded.css',
                                             'package-catalog.js', 'package-catalog.css')]]


def docker(*args):
    result = subprocess.run([DOCKER, *args], capture_output=True, timeout=45)
    if result.returncode:
        (PRIVATE / 'automatic-spug-command-error.private.log').write_bytes(result.stdout + result.stderr)
        raise RuntimeError('SPUG_INSTALL_COMMAND_FAILED')
    return result.stdout


def entry():
    code = """import json,pathlib
out=[]
for p in pathlib.Path('/proc').glob('[0-9]*/cmdline'):
 try:args=p.read_bytes().split(b'\\0')
 except (FileNotFoundError,ProcessLookupError):continue
 if args[:3]==[b'python3',b'-B',b'/opt/intruoyi-spug/smallapp_entry.py']:out.append(int(p.parent.name))
assert len(out)==1,'OWN_ENTRY_PROCESS_AMBIGUOUS'
print(json.dumps(out[0]))
"""
    return json.loads(docker('exec', CONTAINER, 'python3', '-B', '-c', code))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--commit', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    build = json.loads((TASK / ('release-build-' + args.commit[:7] + '.json')).read_text(encoding='utf-8'))
    assert build['status'] == 'PASS' and build['targetCommit'] == args.commit
    root = Path(build['worktree'])
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root).decode().strip() == args.commit
    assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=root).strip()
    container = json.loads(docker('inspect', CONTAINER))[0]
    assert container['Id'] == CONTAINER and container['Name'] == '/intruoyi-spug-transfer-spug-1'
    assert container['HostConfig']['PortBindings']['80/tcp'] == [{'HostIp': '127.0.0.1', 'HostPort': '18080'}]
    mount = next(row for row in container['Mounts'] if row['Destination'] == '/opt/intruoyi-spug')
    assert Path(mount['Source']).as_posix().lower() == RUNTIME.as_posix().lower()
    current_pid = entry()
    plan_path = TASK / ('automatic-spug-install-plan-' + args.commit[:7] + '.json')
    backup_root = PRIVATE / ('spug-before-automatic-' + args.commit[:7])
    pins = {}
    for name in FILES:
        old = (RUNTIME / name).read_bytes()
        new = (root / 'ops/spug' / name).read_bytes()
        if name.endswith('.py'):
            ast.parse(new.decode('utf-8'), filename=name)
        pins[name] = dict(beforeSha256=hashlib.sha256(old).hexdigest(),
                          installedSha256=hashlib.sha256(new).hexdigest(), bytes=len(new))
    plan = dict(status='PLAN_READY', sourceCommit=args.commit, containerId=CONTAINER,
                runtime=str(RUNTIME), previousEntryPid=current_pid, files=pins)
    if not args.apply:
        assert not plan_path.exists()
        write(plan_path, plan)
        print(json.dumps(dict(status='PLAN_READY', fileCount=len(pins), entryPid=current_pid,
                              sourceCommit=args.commit, runtimeWrites=False)))
        raise SystemExit(0)
    assert json.loads(plan_path.read_text(encoding='utf-8')) == plan, 'SPUG_INSTALL_PLAN_CHANGED'
    assert not backup_root.exists(), 'SPUG_INSTALL_ALREADY_STARTED'
    backup_root.mkdir()
    for name in FILES:
        original = RUNTIME / name
        raw = original.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == pins[name]['beforeSha256']
        backup = backup_root / name
        backup.parent.mkdir(parents=True, exist_ok=True)
        backup.write_bytes(raw)
        staged = original.with_name(original.name + '.automatic-' + args.commit[:7] + '.tmp')
        assert not staged.exists()
        with staged.open('xb') as output:
            output.write((root / 'ops/spug' / name).read_bytes())
            output.flush()
            os.fsync(output.fileno())
        os.replace(staged, original)
        assert hashlib.sha256(original.read_bytes()).hexdigest() == pins[name]['installedSha256']
    docker('exec', CONTAINER, 'nginx', '-t')
    docker('exec', CONTAINER, 'nginx', '-s', 'reload')
    assert entry() == current_pid
    code = 'import os,signal;os.kill(' + str(current_pid) + ',signal.SIGTERM)'
    docker('exec', CONTAINER, 'python3', '-B', '-c', code)
    new_pid = None
    for attempt in range(20):
        try:
            pid = entry()
            if pid != current_pid:
                new_pid = pid
                break
        except RuntimeError:
            if attempt == 19:
                raise
        time.sleep(1)
    assert new_pid and new_pid != current_pid, 'OWN_ENTRY_NOT_RELOADED'
    for name in FILES:
        assert hashlib.sha256((RUNTIME / name).read_bytes()).hexdigest() == pins[name]['installedSha256']
    result = dict(plan, status='PASS', observedAt=now(), newEntryPid=new_pid,
                  oldFilesPreserved=True, nginxConfigurationTested=True,
                  sharedServiceRestarted=False, backupPerformed=False, restorePerformed=False)
    write(TASK / ('automatic-spug-installation-' + args.commit[:7] + '.json'), result)
    print(json.dumps({key: value for key, value in result.items() if key != 'files'}))
