"""Push an audited exact commit using an ordinary, non-forced refspec."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit
import winreg

task=Path(__file__).parent
name=sys.argv[1]
assert name in ('source','maintenance')
info=json.loads((task/'repository-inspection.json').read_text('utf-8'))[name]
audit=json.loads((task/'push-audit.json').read_text('utf-8'))[name]
if '--records' in sys.argv[2:]:
    assert name=='maintenance'
    record=json.loads((task/'records-commit.json').read_text('utf-8'))
    assert record['status']=='PASS' and record['credentialScanPassed'] is True and record['parent']==info['commit']
    info=dict(info,commit=record['commit'])
    audit=dict(status='PASS',commit=record['commit'])
assert audit['status']=='PASS' and audit['commit']==info['commit']
repo=info['repository'];branch=info['branch'];commit=info['commit']
if '--push-worktree' in sys.argv[2:]:
    assert name=='source'
    repo='C:/SpugHandoff/schema-push-src-20261101'
python_directory=Path('C:/Users/D01021/Documents/spug-handoff-work-20261030/runtime/Python312-3.12.14')
assert (python_directory/'python.exe').is_file()
git_environment=dict(os.environ,PATH=str(python_directory)+os.pathsep+os.environ['PATH'],PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
git_options=[]
use_system_proxy='--system-proxy' in sys.argv[2:]
if use_system_proxy:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Internet Settings') as key:
        assert winreg.QueryValueEx(key,'ProxyEnable')[0]==1
        address=winreg.QueryValueEx(key,'ProxyServer')[0]
    proxy=urlsplit(address if '://' in address else 'http://'+address)
    assert proxy.hostname=='127.0.0.1' and proxy.port==7890 and not proxy.username and not proxy.password
    git_options=['-c','http.proxy=http://127.0.0.1:7890']

def git(*args,check=True):
    result=subprocess.run(['git','-C',repo,*git_options,*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=180,env=git_environment)
    if check and result.returncode: raise RuntimeError('Git command failed: '+args[0])
    return result

def snapshot():
    index=Path(git('rev-parse','--git-path','index').stdout.decode().strip())
    if not index.is_absolute(): index=Path(repo)/index
    return dict(head=git('rev-parse','HEAD').stdout.decode().strip(),
        indexSha256=hashlib.sha256(index.read_bytes()).hexdigest(),
        statusSha256=hashlib.sha256(git('status','--porcelain','-z').stdout).hexdigest())

assert git('rev-parse','refs/heads/'+branch).stdout.decode().strip()==commit
remote=git('remote','get-url','--push','origin').stdout.decode().strip()
identity=info['remote'].removeprefix('https://github.com/').removesuffix('.git')
assert remote in (info['remote'],info['remote'].removesuffix('.git'),'git@github.com:'+identity+'.git'), 'Remote changed or contains authentication data'
before=snapshot()
start=datetime.now().astimezone().isoformat()
result=git('push','origin',commit+':refs/heads/'+branch,check=False)
output=(result.stdout+result.stderr).decode('utf-8',errors='replace')
safe_output=re.sub(r'(https?://)[^/@\s]+:[^/@\s]+@',r'\1<REDACTED>@',output)
safe_output=re.sub(r'(?i)(password|token|secret|authorization)([=: ]+)\S+',r'\1\2<REDACTED>',safe_output)
reason=None
if result.returncode:
    reason=('non-fast-forward or remote rejection' if 'rejected' in output else
        'authentication failed' if any(t in output.lower() for t in ('authentication','permission denied','could not read username')) else
        'network or Git transport failure')
remote_commit=None
if not result.returncode:
    lines=git('ls-remote','--heads','origin','refs/heads/'+branch).stdout.decode().splitlines()
    assert len(lines)==1
    remote_commit=lines[0].split()[0]
after=snapshot()
report=dict(status='PASS' if result.returncode==0 and remote_commit==commit and before==after else 'BLOCKER',
    repository=name,remote=info['remote'],branch=branch,commit=commit,remoteCommit=remote_commit,
    pushExitCode=result.returncode,startedAt=start,finishedAt=datetime.now().astimezone().isoformat(),
    currentHeadAndIndexPreserved=before==after,forceUsed=False,intMainMerged=False,errorCategory=reason,
    gitOutput=safe_output[:4000],gitOutputTail=safe_output[-5000:],networkRoute='existing-system-proxy' if use_system_proxy else 'Git-default',
    hookPython='bundled-Python-3.12')
prior=task/('push-'+name+'.json')
if prior.exists():
    old=json.loads(prior.read_text('utf-8'))
    stamp=re.sub('[^0-9]','',old['startedAt'])
    archive=task/('push-'+name+'-attempt-'+stamp+'.json')
    if not archive.exists(): archive.write_bytes(prior.read_bytes())
(task/('push-'+name+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
assert report['status']=='PASS','Push did not pass; inspect recorded category, do not force'
