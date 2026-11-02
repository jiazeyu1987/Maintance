"""Commit owned, reviewed final evidence on the task branch, preserving main indexes."""
import json
import os
from pathlib import Path
import re
import subprocess

task=Path(__file__).parent
repo=Path('C:/Users/D01021/Documents/spug-handoff-work-20261030/code/Maintance')
base='43e4d3eb6b85d4f54749d721ad4ec977102a4747'
ref='refs/heads/codex/three-server-schema-20261101'
relative='doc/tasks/20261101-three-server-schema-consistency/'
assert '\ncompleted\n' in (task/'task.md').read_text('utf-8')
release=json.loads((task/'release-result.json').read_text('utf-8'))
for name in ('release-result.json','worktree-closeout.json','slot-closeout.json','cleanup-install-verification.json'):
    assert json.loads((task/name).read_text('utf-8'))['status']=='PASS'
assert not Path('C:/SpugHandoff/schema-ops-20261101').exists()
assert not Path('C:/SpugHandoff/schema-src-20261101').exists()
names={
    'task.md','execution-log.md','request-command-log.md','release-consistency-gate.md','acceptance-report.md','write-acceptance-report.py','candidate.json',
    'red-contract-result.json','green-contract-result.json','verify-regressions.json',
    'real-mysql-migration-result.json','mysql-first-failure-diagnosis.json',
    'programmable-schema-before.json','sealed-package-verification.json',
    'target-gxp-local-local.json','local-install-verification.json','cleanup-install-verification.json',
    'release-result.json','worktree-closeout.json','slot-closeout.json',
    'verify-regressions.py','verify-schema-contracts.py','verify-real-mysql-migration.py',
    'verify-programmable-schema.py','verify-sealed-package.py','publication_proof.py',
    'verify-deployed-phase.py','verify-target-gxp.cjs','collect-schema.py','final-release-report.py',
    'install-committed-schema.py','install-committed-cleanup.py',
    'spug-ui.cjs','spug-action.py','observe-release-progress.py','read-progress.py','wait-job.py',
    'closeout-owned-worktrees.py','release-owned-slot.ps1','commit-final-records.py','prepare-experience-records.py',
}
for env,proof in release['targets'].items():
    names.add('deployed-phase-'+env+'-open.json')
    names.add('target-gxp-'+env+'-'+release['releaseTag']+'.json')
    names.add('remote-'+proof['deploymentJobId']+'-latest.json')
    if env!='test': names.add('deployed-phase-'+env+'-maintenance.json')
private=Path('C:/SpugHandoff/release')
config=json.loads((private/'executor.private.json').read_text('utf-8'))
credentials=[config,json.loads(Path(config['loginVerification']['credentialsFile']).read_text('utf-8-sig')),
    json.loads((private/'private/spug-login.private.json').read_text('utf-8-sig'))]
secret_values=[]
def secrets(value):
    if isinstance(value,dict):
        for key,item in value.items():
            if re.search(r'password|token|secret',key,re.I) and isinstance(item,str) and len(item)>=6:
                secret_values.append(item)
            secrets(item)
    elif isinstance(value,list):
        for item in value: secrets(item)
for item in credentials: secrets(item)
for name in names:
    path=task/name
    text=path.read_text('utf-8')
    assert not re.search(r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',text),'Private key rejected'
    assert not any(secret in text for secret in secret_values),'Private credential content rejected'
    # Normalize only this task's own records to explicit UTF-8/LF.
    path.write_bytes(text.replace('\r\n','\n').encode('utf-8'))

def git(*args,env=None,data=None):
    return subprocess.check_output(['git','-C',str(repo),*args],input=data,env=env)
assert git('rev-parse',ref).decode().strip()==base
head=git('rev-parse','HEAD')
status=git('status','--porcelain','-z')
git_dir=Path(git('rev-parse','--absolute-git-dir').decode().strip())
index=git_dir/'three-server-schema-final.index'
assert not index.exists()
env=dict(os.environ,GIT_INDEX_FILE=str(index))
documents={'docs/'+name:(task/'doc-commit-inputs'/name).read_bytes() for name in ('experience-index.md','release-agent-checklist.md','request-command-log.md')}
for data in documents.values():
    text=data.decode('utf-8')
    assert not any(secret in text for secret in secret_values),'Private credential content rejected'
try:
    git('read-tree',base,env=env)
    for name in sorted(names):
        blob=git('hash-object','-w','--stdin',data=(task/name).read_bytes()).decode().strip()
        assert git('cat-file','-t',blob).decode().strip()=='blob'
        git('update-index','--add','--cacheinfo','100644,'+blob+','+relative+name,env=env)
    for name,data in documents.items():
        blob=git('hash-object','-w','--stdin',data=data).decode().strip()
        assert git('cat-file','-t',blob).decode().strip()=='blob'
        git('update-index','--add','--cacheinfo','100644,'+blob+','+name,env=env)
    assert set(git('diff','--cached','--name-only',base,env=env).decode().splitlines())=={relative+n for n in names}|set(documents)
    git('diff','--cached','--check',base,env=env)
    tree=git('write-tree','--missing-ok',env=env).decode().strip()
    commit=git('commit-tree',tree,'-p',base,data='任务: 记录三服同版本同结构发布验收与收尾\n'.encode('utf-8')).decode().strip()
    git('update-ref',ref,commit,base)
finally:
    index.unlink(missing_ok=True)
assert git('rev-parse','HEAD')==head and git('status','--porcelain','-z')==status
for name in names: assert git('show',commit+':'+relative+name)==(task/name).read_bytes()
for name,data in documents.items(): assert git('show',commit+':'+name)==data
report=dict(status='PASS',implementationCommit=base,finalRecordsCommit=commit,branch=ref,taskRecordFiles=len(names),ownedExperienceDocuments=2,ownedRequestCommandLog=True,mainHeadAndIndexPreserved=True,pushed=False)
(task/'final-records-commit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
