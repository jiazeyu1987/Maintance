"""Commit only verified records owned by this completed restore task."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from preflight import PRIVATE

TASK = Path(__file__).resolve().parent
ROOT = TASK.parents[2]
REQUEST_LOG = 'docs/request-command-log.md'
PREFIX = TASK.relative_to(ROOT).as_posix() + '/'
SUFFIXES = {'.py', '.cjs', '.md', '.json', '.log', '.png'}


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode('utf-8').strip()


def other_files():
    tracked = git('diff', '--name-only').splitlines()
    untracked = git('ls-files', '--others', '--exclude-standard').splitlines()
    return {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in tracked + untracked
        if name and name != REQUEST_LOG and not name.startswith(PREFIX)
    }


if __name__ == '__main__':
    assert git('branch', '--show-current') == 'codex/spug-selectable-restore-targets-20261104'
    assert git('rev-parse', 'HEAD') == 'f819fbedd4dbd389044560d54b215f99a4d59f81'
    already_staged = set(git('diff', '--cached', '--name-only').splitlines())
    assert all(name.startswith(PREFIX) or name == REQUEST_LOG for name in already_staged), 'UNRELATED_STAGED_FILES'
    task_text = (TASK / 'task.md').read_text(encoding='utf-8')
    assert '## Current Status\ncompleted\n' in task_text
    assert json.loads((TASK / 'closeout-verification.json').read_text(encoding='utf-8'))['status'] == 'PASS'
    subprocess.run([sys.executable, '-X', 'utf8', '-B', str(TASK / 'verify_task_records.py')], cwd=ROOT, check=True)
    untouched = other_files()
    selected = sorted(p.relative_to(ROOT).as_posix() for p in TASK.rglob('*')
                      if p.is_file() and (p.suffix in SUFFIXES or p.name == '.gitattributes') and '__pycache__' not in p.parts)
    selected.append(REQUEST_LOG)
    for offset in range(0, len(selected), 30):
        subprocess.run(['git', 'add', '-f', '--', *selected[offset:offset + 30]], cwd=ROOT, check=True)
    assert set(git('diff', '--cached', '--name-only').splitlines()) == set(selected), 'STAGING_SCOPE_CHANGED'
    checked = subprocess.run(['git', 'diff', '--cached', '--check'], cwd=ROOT, capture_output=True)
    if checked.returncode:
        (PRIVATE / 'records-staged-check.private.log').write_bytes(checked.stdout + checked.stderr)
        names = sorted({line.split(':', 1)[0] for line in checked.stdout.decode('utf-8').splitlines() if ': trailing whitespace.' in line or ': new blank line at EOF.' in line})
        print(json.dumps(dict(status='BLOCKER', reason='STAGED_DIFF_CHECK', files=names[:12], fileCount=len(names))))
        raise SystemExit(checked.returncode)
    for name in selected:
        if name.startswith(PREFIX):
            attributes = subprocess.check_output(['git', 'check-attr', '-z', 'text', '--', name], cwd=ROOT).split(b'\x00')
            assert attributes[2] == b'unset', 'RECORD_BYTES_CONVERSION_NOT_DISABLED'
            assert git('hash-object', '--no-filters', '--', name) == git('rev-parse', ':' + name), 'STAGED_BYTES_CHANGED'
    assert other_files() == untouched, 'UNRELATED_FILES_CHANGED'
    committed = subprocess.run(['git', 'commit', '-m', '\u4efb\u52a1: \u5b8c\u6210Spug\u5907\u4efd\u670d\u6062\u590d\u9a8c\u6536\u5f52\u6863'], cwd=ROOT, capture_output=True)
    if committed.returncode:
        (PRIVATE / 'records-commit.private.log').write_bytes(committed.stdout + committed.stderr)
        raise SystemExit('RECORDS_COMMIT_FAILED_SEE_PRIVATE_LOG')
    commit = git('rev-parse', 'HEAD')
    assert set(git('diff-tree', '--no-commit-id', '--name-only', '-r', commit).splitlines()) == set(selected)
    assert not git('diff', '--cached', '--name-only')
    assert not git('status', '--porcelain', '--', PREFIX, REQUEST_LOG)
    assert other_files() == untouched, 'UNRELATED_FILES_CHANGED'
    print(json.dumps(dict(status='PASS', commit=commit, committedFiles=len(selected), unrelatedFilesPreserved=len(untouched))))
