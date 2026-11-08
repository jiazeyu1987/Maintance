"""Commit only the reviewed deployment-contract corrections after real tests."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
from common import TASK, PRIVATE, now, write
from verify_task_records import secrets

ROOT = TASK.parents[2]
FILES = [
    'backend/src/main/resources/recovery_control_incremental_plan.py',
    'ops/recovery/recovery_replace.py',
    'scripts/tests/test_automatic_incremental_plan.py',
    'scripts/tests/test_backup_epoch.py',
    'ops/spug/smallapp-ui/app.js',
    'ops/spug/smallapp_ui_safety.test.cjs',
    'docs/experience-index.md', 'docs/release-agent-checklist.md',
]


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode('utf-8').strip()


if __name__ == '__main__':
    destination = TASK / 'automatic-deployment-contracts-commit.json'
    assert not destination.exists()
    before = git('rev-parse', 'HEAD')
    assert before == '3019c2ebe3e7db0cd607f1a170e5cfbe0879580d'
    assert not git('diff', '--cached', '--name-only')
    report = json.loads((TASK / 'automatic-incremental-deployment-contracts-1.json').read_text(encoding='utf-8'))
    assert report['actualExitCode'] == 0 and report['allTestsActuallyExecuted']
    assert report['containerRemoved'] and report['inputFilesUnchanged']
    for name, sha in report['testedInputSha256'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha, name
    ui = json.loads((TASK / 'automatic-incremental-ui-regression.json').read_text(encoding='utf-8'))
    assert ui['status'] == 'PASS' and ui['exitCode'] == 0
    assert ui['counts'] == dict(tests=83, **{'pass': 83, 'fail': 0, 'cancelled': 0, 'skipped': 0, 'todo': 0})
    for name, data in ui['files'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == data['sha256'], name
    known = set()
    paths = [p for p in PRIVATE.glob('*.json') if p.stat().st_size < 32 * 1024 * 1024]
    paths += [Path('C:/SpugHandoff/release/private') / name for name in ('spug-login.private.json', 'loginCredentials.json')]
    for path in paths:
        secrets(json.loads(path.read_text(encoding='utf-8-sig')), known)
    assert known
    hashes = {}
    for name in FILES:
        raw = (ROOT / name).read_bytes()
        content = raw.decode('utf-8')
        assert not content.startswith('\ufeff') and '\ufffd' not in content, name
        assert not any(value in content for value in known), 'PRIVATE_VALUE_' + name
        if name.endswith('.py'):
            ast.parse(content, filename=name)
        hashes[name] = hashlib.sha256(raw).hexdigest()
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True, capture_output=True)
    subprocess.run(['git', 'add', '--', *FILES], cwd=ROOT, check=True, capture_output=True)
    assert set(git('diff', '--cached', '--name-only').splitlines()) == set(FILES)
    subprocess.run(['git', 'diff', '--cached', '--check'], cwd=ROOT, check=True, capture_output=True)
    subprocess.run(['git', 'commit', '-m', '任务: 修复自动增量真实回执与挂载合同兼容'], cwd=ROOT, check=True)
    commit = git('rev-parse', 'HEAD')
    assert git('rev-parse', commit + '^') == before
    assert set(git('diff-tree', '--no-commit-id', '--name-only', '-r', commit).splitlines()) == set(FILES)
    result = dict(status='PASS', observedAt=now(), previousCommit=before,
                  implementationCommit=commit, files=FILES, testedInputSha256=hashes,
                  privateValuesChecked=len(known), taskAcceptanceComplete=False)
    write(destination, result)
    print(json.dumps({k: v for k, v in result.items() if k not in ('files', 'testedInputSha256')}))
