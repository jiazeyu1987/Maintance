"""Commit only the verified parent-input implementation and its experience gates."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from common import TASK, now, write


ROOT = TASK.parents[2]
FILES = ['ops/backup_engine/standard_fixes.py',
         'ops/backup_engine/formal/formal_capture_parent_guard.py',
         'scripts/tests/test_capture_parent_guard.py', 'scripts/tests/test_backup_variants.py',
         'docs/experience-index.md', 'docs/release-agent-checklist.md']


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode('utf-8').strip()


if __name__ == '__main__':
    assert not (TASK / 'parent-guard-implementation-commit.json').exists()
    before = git('rev-parse', 'HEAD')
    assert before == '6319024c003ead602d59e7697673fa3c39807863'
    assert not git('diff', '--cached', '--name-only'), 'PREEXISTING_STAGED_CHANGES'
    for name in ('parent-guard-red.json', 'parent-guard-red-init.json',
                 'parent-guard-green-4.json', 'parent-guard-regression.json'):
        report = json.loads((TASK / name).read_text(encoding='utf-8'))
        assert report['expectedResultObserved'] and report['containerRemoved']
    for name in ('linux-affected-regression.json', 'linux-parent-final-regression.json'):
        report = json.loads((TASK / name).read_text(encoding='utf-8'))
        assert report['status'] == 'PASS' and report['containerRemoved']
    subprocess.run([sys.executable, '-X', 'utf8', str(TASK / 'verify_task_records.py')], check=True)
    sys.path.insert(0, str(ROOT / 'ops/backup_engine'))
    from build_variants import standard_sources, safe_fixes, canonical
    payload, _ = standard_sources()
    payload = safe_fixes(payload)
    payload['common/repository_minimal.py'] = payload['common/repository_minimal.py'].replace(b"'prod-'", b"'prod-standard-'")
    manifest = {name: hashlib.sha256(raw).hexdigest() for name, raw in sorted(payload.items())}
    for name, raw in payload.items():
        compile(raw, name, 'exec')
    inputs = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in FILES}
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    subprocess.run(['git', 'add', '--', *FILES], cwd=ROOT, check=True)
    assert set(git('diff', '--cached', '--name-only').splitlines()) == set(FILES)
    subprocess.run(['git', 'commit', '-m', '任务: 修复增量父输入检查导致的采集超时'], cwd=ROOT, check=True)
    after = git('rev-parse', 'HEAD')
    assert git('rev-parse', after + '^') == before
    assert set(git('diff-tree', '--no-commit-id', '--name-only', '-r', after).splitlines()) == set(FILES)
    report = dict(status='PASS', observedAt=now(), previousCommit=before, implementationCommit=after,
                  files=FILES, testedInputSha256=inputs, standardFileCount=len(manifest),
                  expectedStandardFileManifestSha256=hashlib.sha256(canonical(manifest)).hexdigest(),
                  taskAcceptanceComplete=False)
    write(TASK / 'parent-guard-implementation-commit.json', report)
    print(json.dumps(report))
