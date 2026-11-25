"""Commit only this task's final records after verified closeout."""
import json, re, subprocess
from pathlib import Path

task=Path(__file__).resolve().parent
repo=task.parents[2]
base=Path('C:/SpugHandoff/release')

def git(*args):
    return subprocess.check_output(['git','-C',str(repo),*args]).decode('utf-8').strip()

assert '\ncompleted\n' in (task/'task.md').read_text(encoding='utf-8')
assert json.loads((task/'release-result.json').read_text(encoding='utf-8'))['status']=='PASS'
assert json.loads((task/'local-closeout-proof.json').read_text(encoding='utf-8'))['status']=='PASS'
assert not git('diff','--cached','--name-only'), 'Existing staged work must be preserved'
prefix=task.relative_to(repo).as_posix()
paths=[p.relative_to(repo).as_posix() for p in task.rglob('*') if p.is_file()]
assert all('__pycache__' not in p and '.private.' not in p for p in paths)
owned_docs={'docs/next-release-menu-repair.md','docs/worktree-memory.md','docs/experience-index.md','docs/release-agent-checklist.md'}
paths.extend(sorted(owned_docs))

protected=[json.loads((base/'executor.private.json').read_text(encoding='utf-8-sig')),
    json.loads((base/'private/loginCredentials.json').read_text(encoding='utf-8-sig'))]
secrets=set()
def collect(value):
    if isinstance(value,dict):
        for k,v in value.items():
            if re.search(r'password|token|secret|bridgeKey|connectionString',k,re.I) and isinstance(v,str) and len(v)>3:
                secrets.add(v)
            collect(v)
    elif isinstance(value,list):
        for v in value:collect(v)
for value in protected:collect(value)
for name in paths:
    data=(repo/name).read_bytes()
    text=data.decode('utf-8')
    assert not re.search(r'-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----',text), 'Private key content rejected'
    assert not any(secret in text for secret in secrets), 'Protected credential content rejected'
    assert '\ufffd' not in text, 'Encoding replacement character rejected'

subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
staged=set(git('diff','--cached','--name-only').splitlines())
assert staged and staged<=set(paths) and all(p.startswith(prefix+'/') or p in owned_docs for p in staged)
subprocess.run(['git','-C',str(repo),'diff','--cached','--check'],check=True)
subprocess.run(['git','-C',str(repo),'commit','-m','任务: 完成IntRuoyi测试和正式发布验收'],check=True)
assert not git('status','--short','--',prefix,*sorted(owned_docs))
print(json.dumps(dict(commit=git('rev-parse','HEAD'),files=len(staged),protectedCredentialScan='PASS',ownedPathsClean=True),ensure_ascii=False))
