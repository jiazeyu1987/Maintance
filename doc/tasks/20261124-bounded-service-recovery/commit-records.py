"""Commit only final task records and this task's shared-log insertion."""
from pathlib import Path
import subprocess

task = Path(__file__).resolve().parent
repo = task.parents[2]
expected = '43ee6e7dba8d72429df936fd6779cebc577fdbba'


def git(*args, data=None):
    result = subprocess.run(['git', '-C', str(repo), *args], input=data, capture_output=True, check=True)
    return result.stdout


assert git('rev-parse', 'HEAD').decode().strip() == expected
assert not git('diff', '--cached', '--name-only').strip()
shared = 'docs/request-command-log.md'
baseline = git('show', 'HEAD:' + shared).decode('utf-8')
working = (repo / shared).read_text(encoding='utf-8')
heading = '## 20261124-bounded-service-recovery\n'
assert heading not in baseline and working.count(heading) == 1
start = working.index(heading)
end = working.index('\n## ', start + len(heading))
section = working[start:end].rstrip() + '\n\n'
first, remainder = baseline.split('\n', 1)
assert first == '# 请求与命令记录'
candidate = first + '\n\n' + section + remainder.lstrip('\n')
blob = git('hash-object', '-w', '--stdin', data=candidate.encode('utf-8')).decode().strip()
git('update-index', '--cacheinfo', '100644,' + blob + ',' + shared)
names = ['task.md', 'execution-log.md', 'check-integration.py', 'integration-preflight.json',
         'closeout-owned.py', 'resource-closeout.json', 'worktree-closeout.json', 'commit-records.py']
paths = [str((task / n).relative_to(repo)).replace('\\', '/') for n in names]
for path in paths:
    (repo / path).read_bytes().decode('utf-8', errors='strict')
git('add', '--', *paths)
git('diff', '--cached', '--check')
actual = set(git('diff', '--cached', '--name-only', '-z').decode('utf-8').strip('\0').split('\0'))
assert actual == set(paths + [shared]), 'Unexpected staged file; preserve index for investigation'
print(git('diff', '--cached', '--stat').decode('utf-8'))
print(git('diff', '--cached', '--', shared).decode('utf-8'))
assert len(git('diff', '--cached', '--', shared).decode('utf-8').splitlines()) < 22
print(git('commit', '-m', '任务: 完成自动恢复验证与收尾记录').decode('utf-8'))
assert not git('diff', '--cached', '--name-only').strip()
assert (repo / shared).read_text(encoding='utf-8') == working
print(git('rev-parse', 'HEAD').decode().strip())
