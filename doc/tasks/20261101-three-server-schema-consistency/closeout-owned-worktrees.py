"""Remove only this task's validated checkouts after all three targets pass."""
from datetime import datetime
import importlib.util
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import psutil

task=Path(__file__).parent
root=Path('C:/SpugHandoff/release')
assert json.loads((task/'release-result.json').read_text('utf-8'))['status']=='PASS'
assert 'ready_for_closeout' in (task/'task.md').read_text('utf-8')
with sqlite3.connect('file:'+str(root/'state/state.sqlite3')+'?mode=ro',uri=True) as db:
    state=json.loads(db.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
assert not any(j['status']=='running' for j in state['jobs'])
config=json.loads((root/'executor.private.json').read_text('utf-8'))
listeners=[s for s in psutil.net_connections('tcp') if s.status==psutil.CONN_LISTEN and s.laddr.port==config['port']]
assert len(listeners)==1
proc=psutil.Process(listeners[0].pid)
assert any(str(root/'source/ops/spug/release-center/intruoyi_executor.py').replace('\\','/').casefold()==a.replace('\\','/').casefold() for a in proc.cmdline())
assert not proc.children(recursive=True)
branch='codex/three-server-schema-20261101'
targets=[
    ('C:/SpugHandoff/schema-src-20261101','C:/Users/D01021/Documents/ChatGPT/IntRuoyi','fb88105af40e4ee6366a20dae2df721f1de2dcb0'),
    ('C:/SpugHandoff/schema-ops-20261101','C:/Users/D01021/Documents/spug-handoff-work-20261030/code/Maintance','43e4d3eb6b85d4f54749d721ad4ec977102a4747'),
]
def git(repo,*args):
    return subprocess.check_output(['git','-c','core.longpaths=true','-C',str(repo),*args])

proofs=[]
for location,repository,commit in targets:
    target=Path(location)
    assert target.resolve()==Path(location) and target.parent.resolve()==Path('C:/SpugHandoff')
    assert not Path.cwd().resolve().is_relative_to(target)
    assert git(target,'rev-parse','HEAD').decode().strip()==commit
    assert git(target,'branch','--show-current').decode().strip()==branch
    assert git(repository,'rev-parse',branch).decode().strip()==commit
    assert not git(target,'status','--porcelain','--untracked-files=all')
    needle=target.as_posix().casefold()
    assert needle in git(repository,'worktree','list','--porcelain').decode().casefold()
    tracked=set(git(target,'ls-files','-z').decode().split('\0'))
    ignored=git(target,'ls-files','--others','--ignored','--exclude-standard','-z').decode().split('\0')
    ignored=[n for n in ignored if n]
    for name in ignored:
        match=re.fullmatch(r'(.+)/__pycache__/([^/]+)\.cpython-312\.pyc',name)
        assert match and match[1]+'/'+match[2]+'.py' in tracked,'Unknown ignored file preserved'
        data=(target/name).read_bytes()
        assert len(data)>=16 and data[:4]==importlib.util.MAGIC_NUMBER and int.from_bytes(data[4:8],'little') in (0,1,3)
    for directory,dirs,files in os.walk(target,followlinks=False):
        for name in dirs+files:
            path=Path(directory)/name
            assert not path.is_symlink() and not (getattr(path.lstat(),'st_file_attributes',0)&0x400),'Link preserved'
    for process in psutil.process_iter(['pid']):
        try:
            cwd=process.cwd().replace('\\','/').casefold().rstrip('/')
            args=process.cmdline()
        except (psutil.NoSuchProcess,psutil.AccessDenied):
            continue
        assert not (cwd==needle or cwd.startswith(needle+'/')),'Worktree consumer exists'
        assert process.pid==os.getpid() or not any(needle in a.replace('\\','/').casefold() for a in args),'Worktree referenced by another process'
    with (task/'execution-log.md').open('a',encoding='utf-8') as log:
        log.write('\nGREEN: experience-preflight -> PASS（本任务checkout收尾）。三服同包/结构/GxP验收通过；精确路径 '+location+'、分支、提交 '+commit+'、干净状态及Git登记已核实；ignored只含合法且有已提交源文件的Python缓存，无链接或消费者。用户明确不自动合入int_main，因此保留独立分支，仅删除本次checkout。\n')
    result=subprocess.run(['git','-c','core.longpaths=true','-C',repository,'worktree','remove',location],capture_output=True,timeout=600)
    assert result.returncode==0,'Git worktree removal failed; preserve evidence'
    assert not os.path.lexists(target)
    assert needle not in git(repository,'worktree','list','--porcelain').decode().casefold()
    assert git(repository,'rev-parse',branch).decode().strip()==commit
    proofs.append(dict(path=location,commit=commit,branch=branch,producedNewCommits=True,branchPreserved=True,mergedIntoIntMain=False,pushed=False,registeredAfter=False,physicalPathExists=False,validatedIgnoredCaches=len(ignored),gitRemovalExitCode=result.returncode))
    print(json.dumps(proofs[-1]),flush=True)
report=dict(status='PASS',time=datetime.now().astimezone().isoformat(),worktrees=proofs,ordinaryExecutorPid=proc.pid,stableRuntimePath=str(root/'source'),otherWorktreesChanged=False)
(task/'worktree-closeout.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
