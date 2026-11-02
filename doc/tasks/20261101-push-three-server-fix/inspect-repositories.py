"""Read-only Git inspection with credential-free remote reporting."""
import json
from pathlib import Path
import subprocess
from urllib.parse import urlsplit

task=Path(__file__).parent
branch='codex/three-server-schema-20261101'
repositories={
    'source':('C:/Users/D01021/Documents/ChatGPT/IntRuoyi','IntRuoyiAll','fb88105af40e4ee6366a20dae2df721f1de2dcb0'),
    'maintenance':('C:/Users/D01021/Documents/spug-handoff-work-20261030/code/Maintance','Maintance','ef647752b14734e4d3849052e5c34d615a73614c'),
}
def git(repo,*args):
    return subprocess.check_output(['git','-C',repo,*args],stderr=subprocess.PIPE).decode('utf-8').strip()

result={}
for name,(repo,expected_repo,expected_commit) in repositories.items():
    remote=git(repo,'remote','get-url','--push','origin')
    if remote.startswith('git@github.com:'):
        identity=remote.removeprefix('git@github.com:').removesuffix('.git')
    else:
        url=urlsplit(remote)
        assert url.hostname=='github.com' and url.scheme in ('https','ssh')
        identity=url.path.strip('/').removesuffix('.git')
    assert identity=='jiazeyu1987/'+expected_repo,'Unexpected remote destination'
    commit=git(repo,'rev-parse','refs/heads/'+branch)
    assert commit==expected_commit,'Task branch changed'
    head=git(repo,'rev-parse','HEAD')
    status=git(repo,'status','--porcelain','-z')
    staged=git(repo,'diff','--cached','--name-only').splitlines()
    refs=git(repo,'ls-remote','--heads','origin').splitlines()
    remote_heads={line.split('\t')[1].removeprefix('refs/heads/'):line.split('\t')[0] for line in refs}
    result[name]=dict(repository=repo,remote='https://github.com/'+identity+'.git',branch=branch,commit=commit,
        currentHead=head,currentBranch=git(repo,'branch','--show-current'),dirtyEntries=len([x for x in status.split('\0') if x]),
        stagedFiles=staged,remoteTargetCommit=remote_heads.get(branch),remoteHeads=remote_heads,
        recentTaskCommits=git(repo,'log','-5','--format=%h %s',branch).splitlines())
(task/'repository-inspection.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for name,info in result.items():
    print(json.dumps(dict(repositoryName=name,**{k:v for k,v in info.items() if k!='remoteHeads'}),ensure_ascii=False))
