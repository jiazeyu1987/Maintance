"""Commit only audited final task records, after actual runtime verification."""
from pathlib import Path
import json, os, subprocess, sys

task = Path(__file__).resolve().parent
for name in ('final-verification.json', 'closeout-verification.json'):
    assert json.loads((task/name).read_text('utf-8'))['status'] == 'PASS'
mode = sys.argv[1]
assert mode in ('source', 'maintenance')
relative = 'doc/tasks/20261102-backend-patch-full-release/'
if mode == 'source':
    repo = Path('C:/SpugHandoff/backend-log-src-20261102')
    files = ['doc/tasks/20261102-backend-patch-startup-noop/'+name for name in ('task.md', 'execution-log.md')]
    message = '任务: 记录启动修复与补丁全量验收'
else:
    repo = task.parents[2]
    files = [p.relative_to(repo).as_posix() for p in task.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    files.append('docs/request-command-log.md')
    message = '任务: 完成后端补丁衔接全量发布验收'
environment = dict(os.environ, PYTHONUTF8='1')
environment['PATH'] = 'C:/Users/D01021/Documents/spug-handoff-work-20261030/runtime/Python312-3.12.14;'+environment['PATH']
def git(*args):
    value = subprocess.run(['git', *args], cwd=repo, env=environment, capture_output=True, timeout=120)
    assert value.returncode == 0, 'Git step failed: '+args[0]
    return value.stdout.decode('utf-8').strip()
assert not git('diff', '--cached', '--name-only'), 'Preserve unrelated staged changes'
git('diff', '--check')
tracked = git('diff', '--name-only').splitlines()
untracked = git('ls-files', '--others', '--exclude-standard').splitlines()
assert set(tracked+untracked) <= set(files), 'Unrelated work must be preserved and reviewed separately'
for name in files:
    (repo/name).read_text('utf-8')
git('add', '--', *files)
staged = git('diff', '--cached', '--name-only').splitlines()
assert staged and set(staged) <= set(files)
git('diff', '--cached', '--check')
private = Path('C:/SpugHandoff/release/private/backend-patch-full-release-20261102')
log = private/('final-records-'+mode+'-commit.private.log')
assert not log.exists(), 'Preserve previous commit evidence'
with log.open('wb') as stream:
    result = subprocess.run(['git', 'commit', '-m', message], cwd=repo, env=environment, stdout=stream, stderr=subprocess.STDOUT, timeout=180)
assert result.returncode == 0, 'Final documentation commit rejected; inspect private hook output'
commit = git('rev-parse', 'HEAD')
assert set(git('show', '--pretty=', '--name-only', 'HEAD').splitlines()) == set(staged)
report = dict(status='PASS', repository=mode, commit=commit, files=len(staged), noMergeOrPush=True)
if mode == 'source':
    (task/'source-closeout-commit.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print(json.dumps(report))
