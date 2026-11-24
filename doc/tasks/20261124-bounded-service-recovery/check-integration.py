"""Read-only source/index/overlap proof; writes only this task's receipt."""
import hashlib
import json
from pathlib import Path
import subprocess

task = Path(__file__).resolve().parent
repo = task.parents[2]
commit = '43ee6e7dba8d72429df936fd6779cebc577fdbba'
base = 'da07ac5a40c5cd397528636a056eb73764c93c9f'


def git(*args):
    return subprocess.check_output(['git', '-C', str(repo), *args])


assert git('branch', '--show-current').strip() == b'int_main'
assert not git('diff', '--cached', '--name-only').strip()
assert git('rev-parse', 'HEAD').decode().strip() == base
git('merge-base', '--is-ancestor', base, commit)
paths = [p.decode('utf-8') for p in git('diff-tree', '--no-commit-id', '--name-only', '-r', '-z', commit).split(b'\0') if p]
assert len(paths) == 8
overlap = []
for name in paths:
    target = repo / name
    if git('status', '--porcelain', '--untracked-files=all', '--', name).strip():
        overlap.append(name)
    tracked = bool(git('ls-files', '--', name).strip())
    if target.exists() and not tracked:
        overlap.append(name)
raw = git('status', '--porcelain=v1', '-z', '--untracked-files=all')
result = dict(mainHead=base, implementationCommit=commit, branch='int_main',
              paths=paths, overlap=sorted(set(overlap)), initialIndexEmpty=True,
              unrelatedStatusSha256=hashlib.sha256(raw).hexdigest(),
              unrelatedStatusEntries=len([v for v in raw.split(b'\0') if v]))
(task / 'integration-preflight.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result))
assert not overlap, 'Protected merge overlap; preserve all workspaces'
