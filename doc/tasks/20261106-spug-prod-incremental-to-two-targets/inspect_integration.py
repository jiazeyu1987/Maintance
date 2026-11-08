"""Read-only inventory of exact incoming paths and protected main changes."""
import hashlib
import json
import subprocess
from pathlib import Path
from common import TASK, now, write

ROOT = TASK.parents[2]
MAIN = Path('C:/Users/D01021/Documents/ChatGPT/Maintance')

def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args]).decode('utf-8').strip()

if __name__ == '__main__':
    main = git(MAIN, 'rev-parse', 'HEAD')
    branch = git(ROOT, 'rev-parse', 'HEAD')
    base = git(ROOT, 'merge-base', main, branch)
    incoming = set(git(ROOT, 'diff', '--name-only', base, branch).splitlines())
    outgoing = set(git(ROOT, 'diff', '--name-only', base, main).splitlines())
    raw = subprocess.check_output(['git', '-C', str(MAIN), 'status', '--porcelain=v1', '-z', '--untracked-files=all']).decode('utf-8')
    rows = [item for item in raw.split('\0') if item]
    assert all(row[2] == ' ' and 'R' not in row[:2] and 'C' not in row[:2] for row in rows), 'EXPLICIT_RENAME_REVIEW_REQUIRED'
    dirty = {row[3:]: row[:2] for row in rows}
    overlaps = sorted(path for path in dirty if path in incoming or any(p.startswith(path.rstrip('/') + '/') for p in incoming))
    pins = {}
    for name in overlaps:
        path = MAIN / name
        assert path.is_file() and not path.is_symlink(), 'OVERLAP_NOT_REGULAR_FILE'
        data = path.read_bytes()
        pins[name] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), gitStatus=dirty[name])
    report = dict(status='READ_ONLY', observedAt=now(), mainPath=str(MAIN), mainCommit=main,
        taskCommit=branch, mergeBase=base, mainBranch=git(MAIN, 'branch', '--show-current'),
        mainIndexEmpty=not git(MAIN, 'diff', '--cached', '--name-only'),
        dirtyFileCount=len(dirty), incomingFileCount=len(incoming),
        mainCommittedChanges=sorted(outgoing), committedOverlap=sorted(incoming & outgoing),
        dirtyIncomingOverlap=pins, noMainChanges=True)
    write(TASK / 'integration-readonly-preflight.json', report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('dirtyIncomingOverlap','mainCommittedChanges','committedOverlap')}, ensure_ascii=False))
    print(json.dumps(dict(dirtyOverlap=list(pins), committedOverlap=report['committedOverlap']), ensure_ascii=False))
