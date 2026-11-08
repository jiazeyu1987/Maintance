"""Commit exact reviewed catalogue implementation and tested baseline only."""
import ast
import hashlib
import json
import subprocess
from pathlib import Path
from common import TASK, PRIVATE, now, write
from verify_task_records import secrets

ROOT = TASK.parents[2]
FILES = ['ops/spug/release-center/' + name for name in (
    'application_registry.py', 'executor.py', 'release_http.py', 'package_catalog.py',
    'package_presence.py', 'test_release_identity.py', 'test_package_catalog.py',
    'test_package_presence.py', 'test_commit_catalog.py', 'README.md')]
FILES += ['docs/experience-index.md', 'docs/release-agent-checklist.md']

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode('utf-8').strip()

if __name__ == '__main__':
    destination = TASK / 'catalogue-identity-implementation-commit.json'
    assert not destination.exists()
    previous = git('rev-parse', 'HEAD')
    assert previous == '0d445782dc06995b3c84b1b45146ea4b75483f92'
    assert not git('diff', '--cached', '--name-only')
    win = json.loads((TASK / 'catalogue-identity-regression.json').read_text(encoding='utf-8'))
    linux = json.loads((TASK / 'catalogue-identity-linux.json').read_text(encoding='utf-8'))
    assert win['exitCode'] == linux['exitCode'] == 0 and win['sourceUnchanged'] and linux['sourceUnchanged']
    assert linux['containerRemoved'] and linux['network'] == 'none' and linux['readOnlyBind']
    for name, pin in win['sourcePins'].items():
        assert hashlib.sha256((ROOT / 'ops/spug/release-center' / name).read_bytes()).hexdigest() == pin['sha256'], name
    for name, sha in linux['sourcePins'].items():
        assert hashlib.sha256((ROOT / 'ops/spug/release-center' / name).read_bytes()).hexdigest() == sha, name
    known = set()
    paths = [p for p in PRIVATE.glob('*.json') if p.stat().st_size < 32 * 1024 * 1024]
    paths += [Path('C:/SpugHandoff/release/private') / name for name in ('spug-login.private.json', 'loginCredentials.json')]
    for path in paths:
        secrets(json.loads(path.read_text(encoding='utf-8-sig')), known)
    assert known
    pins = {}
    for name in FILES:
        data = (ROOT / name).read_bytes()
        text = data.decode('utf-8')
        assert not text.startswith('\ufeff') and '\ufffd' not in text
        assert not any(value in text for value in known), 'PRIVATE_VALUE_' + name
        if name.endswith('.py'):
            ast.parse(text, filename=name)
        pins[name] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    subprocess.run(['git', 'diff', '--check', '--', *FILES], cwd=ROOT, check=True, capture_output=True)
    subprocess.run(['git', 'add', '--', *FILES], cwd=ROOT, check=True, capture_output=True)
    assert set(git('diff', '--cached', '--name-only').splitlines()) == set(FILES)
    subprocess.run(['git', 'diff', '--cached', '--check'], cwd=ROOT, check=True, capture_output=True)
    subprocess.run(['git', 'commit', '-m', '任务: 消除包清单身份校验的历史全量读取'], cwd=ROOT, check=True)
    commit = git('rev-parse', 'HEAD')
    assert git('rev-parse', commit + '^') == previous
    assert set(git('diff-tree', '--no-commit-id', '--name-only', '-r', commit).splitlines()) == set(FILES)
    result = dict(status='PASS', observedAt=now(), previousCommit=previous, implementationCommit=commit,
        files=pins, privateValuesChecked=len(known), windowsRegressionTests=66, linuxRegressionTests=15,
        actualInstallationComplete=False, taskAcceptanceComplete=False)
    write(destination, result)
    print(json.dumps({k:v for k,v in result.items() if k != 'files'}))
