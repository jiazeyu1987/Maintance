"""Read-only closeout audit; print identities and counts, never private values."""
from pathlib import Path
import hashlib, json, re, sqlite3, subprocess, sys
import psutil

task = Path(__file__).resolve().parent
root = Path('C:/SpugHandoff/release')
private = root/'private/backend-patch-full-release-20261102/runtime-stopped-patch'
before = json.loads((private/'before.json').read_text('utf-8'))
assert hashlib.sha256((root/'executor.private.json').read_bytes()).hexdigest() == before['configSha256']
installed={row['name']:row for row in json.loads((private/'code-update-plan.json').read_text('utf-8'))}
for phase in ('runtime-cleanup','runtime-cleanup-legacy'):
    cleanup_private=root/'private/backend-patch-full-release-20261102'/phase
    assert json.loads((cleanup_private/'verification.json').read_text('utf-8'))['status']=='passed'
    installed.update({row['name']:row for row in json.loads((cleanup_private/'code-update-plan.json').read_text('utf-8'))})
for row in installed.values():
    assert hashlib.sha256((root/'source/ops/spug/release-center'/row['name']).read_bytes()).hexdigest()==row['afterSha256']
owners = {c.pid for c in psutil.net_connections(kind='tcp') if c.status == 'LISTEN' and c.laddr.port == 18112}
assert owners == {14264}, 'Stable executor identity changed'
process = psutil.Process(14264)
assert (root/'source/ops/spug/release-center/intruoyi_executor.py').as_posix() in [v.replace('\\', '/') for v in process.cmdline()]
with sqlite3.connect('file:'+str(root/'state/state.sqlite3').replace('\\', '/')+'?mode=ro', uri=True) as db:
    state = json.loads(db.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
assert not any(j['status'] in ('running', 'queued') for j in state['jobs'])
assert not list((root/'build').glob('*')), 'Unexpected remaining build workspace; preserve and inspect'

def git(*args, cwd=None):
    result = subprocess.run(['git', *args], cwd=cwd, capture_output=True, timeout=90)
    assert result.returncode == 0, 'Git audit failed'
    return result.stdout.decode('utf-8').strip()

source = Path('C:/SpugHandoff/backend-log-src-20261102')
selection = json.loads((task/'selected-release.json').read_text('utf-8'))
# Final documentation commit may be a descendant; published source stays fixed.
git('merge-base', '--is-ancestor', selection['commit'], 'HEAD', cwd=source)
assert not git('diff', selection['commit'], 'HEAD', '--', 'IntRuoyiBackend', 'IntRuoyiFronted', cwd=source)
worktrees = git('worktree', 'list', '--porcelain', cwd=source)
assert 'C:/SpugHandoff/release/build/' not in worktrees

config = json.loads((root/'executor.private.json').read_text('utf-8'))
credential_files = [root/'private/spug-login.private.json']
business = config.get('loginVerification', {}).get('credentialsFile')
if business:
    credential_files.append(Path(business))
secrets = []
def collect(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if re.search(r'password|passwd|secret|token', key, re.I) and isinstance(item, str) and len(item) >= 8:
                secrets.append(item)
            collect(item)
    elif isinstance(value, list):
        for item in value:
            collect(item)
collect(config)
for path in credential_files:
    collect(json.loads(path.read_text('utf-8')))
files = [p for p in task.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
assert all(p.suffix in {'.py', '.cjs', '.ps1', '.json', '.md'} for p in files)
for path in files:
    data = path.read_text('utf-8')
    assert not any(value in data for value in secrets), 'Private value found in task file: '+path.name
    assert not re.search(r'-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----', data), 'Private key found: '+path.name
    assert '\ufffd' not in data, 'Replacement character found: '+path.name
report = dict(status='PASS',ordinaryExecutorPid=14264,stableExecutorPath=True,privateConfigUnchanged=True,
    committedRuntimeDeltaUnchanged=True,noActiveJobs=True,noBuildWorktree=True,
    publishedSourceCommit=selection['commit'],sourceProgramUnchanged=True,
    developmentBranchesPreserved=True,noIntMainMergeOrPush=True,utf8Files=len(files),credentialScanPassed=True)
output = task/'closeout-verification.json'
if '--check' not in sys.argv:
    assert not output.exists(), 'Preserve earlier closeout evidence'
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(report))
