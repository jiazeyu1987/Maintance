"""Commit the explicitly reviewed automatic-backup implementation only."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from common import TASK, PRIVATE, now, write
from verify_task_records import secrets

ROOT = TASK.parents[2]
FILES = [
    'backend/src/main/resources/recovery_control_incremental_plan.py',
    'backend/src/main/resources/recovery_control_smallapp.py',
    'backend/src/main/resources/recovery_control_smallapp_http.py',
    'backend/src/main/resources/recovery_control_smallapp_native.py',
    'docs/experience-index.md', 'docs/release-agent-checklist.md',
    'ops/backup_engine/files.json', 'ops/backup_engine/standard_fixes.py',
    'ops/recovery/recovery_backup_epoch.py', 'ops/recovery/recovery_sql_stream.py',
    'ops/recovery/recovery_data.py', 'ops/recovery/recovery_replace.py',
    'ops/spug/README.md', 'ops/spug/smallapp-entry.locations.conf',
    'ops/spug/smallapp_adapter.py', 'ops/spug/smallapp_entry.py',
    'ops/spug/smallapp_ui_safety.test.cjs',
    'ops/spug/smallapp-ui/app.js', 'ops/spug/smallapp-ui/index.html',
    'ops/spug/smallapp-ui/simple.css', 'ops/spug/smallapp-ui/simple.js',
    'ops/spug/smallapp-ui/embedded.css', 'ops/spug/smallapp-ui/embedded.js',
    'ops/spug/smallapp-ui/embedded.test.cjs',
    'ops/spug/smallapp-ui/package-catalog-dialog.test.cjs',
    'ops/spug/smallapp-ui/package-catalog.css', 'ops/spug/smallapp-ui/package-catalog.js',
    'ops/spug/smallapp-ui/package-catalog.test.cjs',
    'ops/spug/test_automatic_incremental_entry.py',
    'ops/spug/test_automatic_incremental_http.py',
    'ops/spug/test_automatic_incremental_proxy.py',
    'ops/spug/test_smallapp_bridge_errors.py',
    'scripts/tests/test_automatic_incremental_plan.py',
    'scripts/tests/test_automatic_incremental_resilience.py',
    'scripts/tests/test_backup_epoch.py', 'scripts/tests/test_incremental_sql_stream.py',
    'scripts/tests/test_backup_variants.py',
]


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode('utf-8').strip()


if __name__ == '__main__':
    output = TASK / 'automatic-incremental-implementation-commit.json'
    assert not output.exists()
    before = git('rev-parse', 'HEAD')
    assert before == '0c5828a63e387fe55594450bf2121cd4b31a7d8a'
    assert not git('diff', '--cached', '--name-only')
    for group in ('stream-epoch-5', 'control-1', 'regression-1'):
        report = json.loads((TASK / ('automatic-incremental-' + group + '.json')).read_text(encoding='utf-8'))
        assert report['actualExitCode'] == 0 and report['allTestsActuallyExecuted']
        assert report['containerRemoved'] and report['inputFilesUnchanged']
        for name, expected in report['testedInputSha256'].items():
            assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, 'TESTED_INPUT_CHANGED_' + name
    known = set()
    private_files = [p for p in PRIVATE.glob('*.json') if p.stat().st_size < 32 * 1024 * 1024]
    private_files += [Path('C:/SpugHandoff/release/private') / name
                      for name in ('spug-login.private.json', 'loginCredentials.json')]
    for path in private_files:
        secrets(json.loads(path.read_text(encoding='utf-8-sig')), known)
    assert known
    inputs = {}
    for name in FILES:
        path = ROOT / name
        raw = path.read_bytes()
        content = raw.decode('utf-8')
        assert '\ufffd' not in content and not content.startswith('\ufeff'), 'ENCODING_INVALID_' + name
        assert not any(value in content for value in known), 'PRIVATE_VALUE_IN_' + name
        assert not re.search(r'(?m)^-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----\s*$', content)
        if path.suffix == '.py':
            ast.parse(content, filename=name)
        if path.suffix == '.json':
            json.loads(content)
        inputs[name] = hashlib.sha256(raw).hexdigest()
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True, capture_output=True)
    subprocess.run(['git', 'add', '--', *FILES], cwd=ROOT, check=True, capture_output=True)
    assert set(git('diff', '--cached', '--name-only').splitlines()) == set(FILES)
    subprocess.run(['git', 'diff', '--cached', '--check'], cwd=ROOT, check=True, capture_output=True)
    subprocess.run(['git', 'commit', '-m', '任务: 实现Spug自动增量基线与持续任务跟踪'], cwd=ROOT, check=True)
    after = git('rev-parse', 'HEAD')
    assert git('rev-parse', after + '^') == before
    assert set(git('diff-tree', '--no-commit-id', '--name-only', '-r', after).splitlines()) == set(FILES)
    result = dict(status='PASS', observedAt=now(), previousCommit=before,
                  implementationCommit=after, files=FILES, testedInputSha256=inputs,
                  privateValuesChecked=len(known), taskAcceptanceComplete=False)
    write(output, result)
    print(json.dumps({k: v for k, v in result.items() if k not in ('files', 'testedInputSha256')}))
