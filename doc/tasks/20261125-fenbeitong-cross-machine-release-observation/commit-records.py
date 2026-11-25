"""Select this task's records; preserve unrelated changes in the shared log."""
from pathlib import Path
import subprocess

task = Path(__file__).resolve().parent
repo = task.parents[2]


def git(*args, data=None):
    return subprocess.run(['git', '-C', str(repo), *args], input=data,
                          capture_output=True, check=True).stdout


assert git('branch', '--show-current').strip() == b'int_main'
assert not git('diff', '--cached', '--name-only').strip()
shared = 'docs/request-command-log.md'
baseline = git('show', 'HEAD:' + shared).decode('utf-8')
working = (repo / shared).read_text(encoding='utf-8')
heading = '## 20261125-fenbeitong-cross-machine-release-observation\n'
assert heading not in baseline and working.count(heading) == 1
start = working.index(heading)
end = working.index('\n## ', start + len(heading))
section = working[start:end].rstrip() + '\n\n'
first, remainder = baseline.split('\n', 1)
candidate = first + '\n\n' + section + remainder.lstrip('\n')
blob = git('hash-object', '-w', '--stdin', data=candidate.encode('utf-8')).decode().strip()
git('update-index', '--cacheinfo', '100644,' + blob + ',' + shared)
names = ['task.md', 'execution-log.md', 'observe.py', 'analyze.py', 'remote-observation.json',
         'summary.json', 'commit-records.py']
paths = [(task / n).relative_to(repo).as_posix() for n in names]
for path in paths:
    raw = (repo / path).read_bytes()
    raw.decode('utf-8', errors='strict')
    assert not raw.startswith(b'\xef\xbb\xbf')
git('add', '--', *paths)
git('diff', '--cached', '--check')
actual = set(git('diff', '--cached', '--name-only', '-z').decode('utf-8').strip('\0').split('\0'))
assert actual == set(paths + [shared])
assert len(git('diff', '--cached', '--', shared).decode('utf-8').splitlines()) < 22
print(git('diff', '--cached', '--stat').decode('utf-8'))
print(git('commit', '-m', '任务: 核实跨机器分贝通发布状态').decode('utf-8'))
assert (repo / shared).read_text(encoding='utf-8') == working
assert not git('diff', '--cached', '--name-only').strip()
print(git('rev-parse', 'HEAD').decode().strip())
