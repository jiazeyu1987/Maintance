"""Verify only this task's resources and the executor's stable path after closeout."""
import hashlib,json,subprocess
from pathlib import Path
import psutil
task=Path(__file__).resolve().parent
base=Path('C:/SpugHandoff/release'); private=base/'private/intruoyi-fenbeitong-test-prod-20261125'
installed=json.loads((private/'installation-result.json').read_text(encoding='utf-8'))
assert hashlib.sha256((base/'executor.private.json').read_bytes()).hexdigest()==installed['configBeforeSha256']
assert hashlib.sha256((base/'source/ops/spug/release-center/intruoyi_runtime_agent.py').read_bytes()).hexdigest()=='9ab3ff40bc838a7c711308a6f762ff2528d5ccd86da1ea6e5164a5f417333f83'
p=psutil.Process(installed['newPid']); args=p.cmdline()
assert p.is_running() and any(Path(x).as_posix().lower()==(base/'source/ops/spug/release-center/intruoyi_executor.py').as_posix().lower() for x in args)
assert any(Path(x).as_posix().lower()==(base/'executor.private.json').as_posix().lower() for x in args)
before_process=json.loads((private/'before-install/process.private.json').read_text(encoding='utf-8'))
assert Path(p.cwd()).resolve()==Path(before_process['cwd']).resolve()
source=Path('C:/Users/D01021/Documents/ChatGPT/IntRuoyi')
def git(repo,*args):return subprocess.check_output(['git','-C',str(repo),*args]).decode('utf-8').strip()
trees=[base/'build/2026-11-25-23-53-05',base/'build/2026-11-26-00-12-02',base/'build/2026-11-26-01-52-12',
       base/'registration-config-release-fix-20261126',base/'fenbeitong-ticket-tenant-20261126',base/'intruoyi-fenbeitong-release-20261125']
registration=git(source,'worktree','list','--porcelain')+'\n'+git(task.parents[2],'worktree','list','--porcelain')
for path in trees:assert not path.exists() and path.as_posix() not in registration
subprocess.run(['git','-C',str(source),'merge-base','--is-ancestor','eb866bbaf4ea1b1c6db93daa63e77576766c3684','int_main'],check=True)
common=Path(git(source,'rev-parse','--path-format=absolute','--git-common-dir'))
registry=json.loads((common/'intrruoyi-runtime/worktree-ports.json').read_text(encoding='utf-8-sig'))
slots=[]
for name,slot in [('registration-config-release-fix-20261126',9),('fenbeitong-ticket-tenant-20261126',10)]:
    rows=[x for x in registry['worktrees'] if x['name']==name]
    assert len(rows)==1 and rows[0]['slot']==slot and rows[0]['active'] is False
    slots.append(dict(name=name,slot=slot,active=False))
v=dict(status='PASS',executorPid=p.pid,stableExecutorPathVerified=True,stableExecutorCwdVerified=True,privateConfigBytesPreserved=True,
       installedAgentMatchesCommit=True,ownedWorktreesAbsent=[str(p) for p in trees],slots=slots,sourceFixInIntMain=True)
(task/'local-closeout-proof.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(v,ensure_ascii=False))
