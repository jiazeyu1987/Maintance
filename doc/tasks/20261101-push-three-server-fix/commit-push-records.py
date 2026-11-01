"""Commit only this task's records using an isolated index; preserve workspaces."""
import json
import os
from pathlib import Path
import re
import subprocess

task=Path(__file__).parent
repo='C:/Users/D01021/Documents/spug-handoff-work-20261030/code/Maintance'
parent='ef647752b14734e4d3849052e5c34d615a73614c'
ref='refs/heads/codex/three-server-schema-20261101'
relative='doc/tasks/20261101-push-three-server-fix/'
assert '\ncompleted\n' in (task/'task.md').read_text('utf-8')
for name in ('push-source.json','push-maintenance.json','worktree-closeout.json','slot-closeout.json'):
    assert json.loads((task/name).read_text('utf-8'))['status']=='PASS'

def git(*args,data=None,env=None):
    r=subprocess.run(['git','-C',repo,*args],input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
    if r.returncode:
        if args[0]=='diff': print(r.stdout.decode('utf-8',errors='replace')[-5000:])
        raise RuntimeError('Git record command failed: '+args[0])
    return r.stdout

root=Path('C:/SpugHandoff/release')
config=json.loads((root/'executor.private.json').read_text('utf-8-sig'))
values=set()
def collect(value):
    if isinstance(value,dict):
        for key,item in value.items():
            if re.search('password|token|secret',key,re.I) and not re.search('(file|path|name)$',key,re.I) and isinstance(item,str) and len(item)>=6: values.add(item)
            collect(item)
    elif isinstance(value,list):
        for item in value: collect(item)
for item in (config,json.loads(Path(config['loginVerification']['credentialsFile']).read_text('utf-8-sig')),
             json.loads((root/'private/spug-login.private.json').read_text('utf-8-sig'))): collect(item)
names={'task.md','execution-log.md','request-command-log.md','inspect-repositories.py','repository-inspection.json','audit-push.py','push-audit.json',
    'inspect-audit-match.py','push-branch.py','push-source.json','push-maintenance.json','cleanup-push-worktree.py',
    'worktree-closeout.json','release-owned-slot.ps1','slot-closeout.json','commit-push-records.py'}
names.update(p.name for p in task.glob('push-*-attempt-*.json'))
data={relative+n:(task/n).read_text('utf-8').replace('\r\n','\n').encode('utf-8') for n in names}
header='## 2026-11-01 提交推送三服一致性修复'
shared=Path('C:/Users/D01021/Documents/ChatGPT/Maintance/docs/request-command-log.md')
current=shared.read_text('utf-8')
assert current.count(header)==1
owned=current[current.index(header):]
baseline=git('show',parent+':docs/request-command-log.md').decode('utf-8')
assert header not in baseline
data['docs/request-command-log.md']=(baseline.rstrip()+'\n\n'+owned).encode('utf-8')
for content in data.values():
    text=content.decode('utf-8')
    assert not any(value in text for value in values),'Private credential rejected'
    assert not re.search(r'(?m)^-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----\r?\n[A-Za-z0-9+/=]{20,}',text)
    assert len(content)<100_000_000
assert git('rev-parse',ref).decode().strip()==parent
head=git('rev-parse','HEAD');status=git('status','--porcelain','-z')
git_dir=Path(git('rev-parse','--absolute-git-dir').decode().strip())
index=git_dir/'push-three-server-fix.index'
assert not index.exists()
env=dict(os.environ,GIT_INDEX_FILE=str(index))
try:
    git('read-tree',parent,env=env)
    for path,content in sorted(data.items()):
        blob=git('hash-object','-w','--stdin',data=content).decode().strip()
        git('update-index','--add','--cacheinfo','100644,'+blob+','+path,env=env)
    assert set(git('diff','--cached','--name-only',parent,env=env).decode().splitlines())==set(data)
    git('diff','--cached','--check',parent,env=env)
    tree=git('write-tree','--missing-ok',env=env).decode().strip()
    commit=git('commit-tree',tree,'-p',parent,data='任务: 记录三服修复Git推送与工作区收尾\n'.encode('utf-8')).decode().strip()
    git('update-ref',ref,commit,parent)
finally: index.unlink(missing_ok=True)
assert git('rev-parse','HEAD')==head and git('status','--porcelain','-z')==status
for path,content in data.items(): assert git('show',commit+':'+path)==content
result=dict(status='PASS',commit=commit,parent=parent,branch=ref,recordFiles=len(data),
    credentialScanPassed=True,largestRecordBytes=max(map(len,data.values())),mainHeadAndIndexPreserved=True)
(task/'records-commit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
