"""Commit only the frozen allocator implementation already verified on Linux."""
import hashlib
import json
import subprocess
import sys
from common import TASK, now, write

ROOT = TASK.parents[2]
FILES = ['ops/backup_engine/formal/formal_schema_evidence.py',
         'ops/recovery/recovery_data.py', 'ops/backup_engine/standard_fixes.py',
         'scripts/tests/test_frozen_auto_increment.py', 'scripts/tests/test_backup_variants.py',
         'docs/experience-index.md', 'docs/release-agent-checklist.md']

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode('utf8').strip()

if __name__ == '__main__':
    output = TASK / 'allocator-implementation-commit.json'
    assert not output.exists()
    before = git('rev-parse', 'HEAD')
    assert before == 'd487abf28ae38c2e6db445d8b888bf06b32df4e5'
    assert not git('diff', '--cached', '--name-only'), 'PREEXISTING_STAGED_CHANGES'
    regression = json.loads((TASK / 'allocator-regression-4.json').read_text(encoding='utf8'))
    assert regression['actualExitCode'] == 0 and regression['expectedResultObserved']
    assert regression['containerRemoved'] and regression['isolatedProcesses'] and regression['inputFilesUnchanged']
    for name, sha in regression['testedInputSha256'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha, 'TESTED_INPUT_CHANGED'
    for name, status in [('allocator-real-red.json','EXPECTED_RED'),
                         ('allocator-real-green-3.json','PASS'), ('allocator-real-frozen-plan.json','PASS'),
                         ('allocator-real-resource-cleanup.json','PASS')]:
        assert json.loads((TASK / name).read_text(encoding='utf8'))['status'] == status
    subprocess.run([sys.executable, '-X', 'utf8', str(TASK / 'verify_task_records.py')], check=True)
    inputs = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in FILES}
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    subprocess.run(['git', 'add', '--', *FILES], cwd=ROOT, check=True)
    assert set(git('diff', '--cached', '--name-only').splitlines()) == set(FILES)
    subprocess.run(['git', 'commit', '-m', '任务: 恢复增量备份冻结的自增序号状态'], cwd=ROOT, check=True)
    after = git('rev-parse', 'HEAD')
    assert git('rev-parse', after + '^') == before
    assert set(git('diff-tree','--no-commit-id','--name-only','-r',after).splitlines()) == set(FILES)
    report = dict(status='PASS', observedAt=now(), previousCommit=before, implementationCommit=after,
                  files=FILES, testedInputSha256=inputs, taskAcceptanceComplete=False)
    write(output, report);print(json.dumps(report))
