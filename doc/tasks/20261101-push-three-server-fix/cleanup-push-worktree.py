"""Remove only this task's clean, successfully pushed Git checkout."""
from datetime import datetime
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import psutil

task=Path(__file__).parent
target=Path('C:/SpugHandoff/schema-push-src-20261101')
repo='C:/Users/D01021/Documents/ChatGPT/IntRuoyi'
commit='fb88105af40e4ee6366a20dae2df721f1de2dcb0'
branch='codex/three-server-schema-20261101'
proof=json.loads((task/'push-source.json').read_text('utf-8'))
assert proof['status']=='PASS' and proof['remoteCommit']==commit
assert target.resolve()==target and target.parent==Path('C:/SpugHandoff')
def git(location,*args):
    return subprocess.check_output(['git','-C',str(location),*args],stderr=subprocess.PIPE)
assert git(target,'rev-parse','HEAD').decode().strip()==commit
assert git(target,'branch','--show-current').decode().strip()==branch
assert not git(target,'status','--porcelain','--untracked-files=all')
tracked=set(git(target,'ls-files','-z').decode().split('\0'))
ignored=[p for p in git(target,'ls-files','--others','--ignored','--exclude-standard','-z').decode().split('\0') if p]
for name in ignored:
    match=re.fullmatch(r'(.+)/__pycache__/([^/]+)\.cpython-312\.pyc',name)
    assert match and match[1]+'/'+match[2]+'.py' in tracked
    content=(target/name).read_bytes()
    assert len(content)>=16 and content[:4]==importlib.util.MAGIC_NUMBER and int.from_bytes(content[4:8],'little') in (0,1,3)
needle=target.as_posix().casefold()
for proc in psutil.process_iter(['pid']):
    try: cwd=proc.cwd().replace('\\','/').casefold();args=proc.cmdline()
    except (psutil.NoSuchProcess,psutil.AccessDenied): continue
    assert not (cwd==needle or cwd.startswith(needle+'/'))
    assert proc.pid==os.getpid() or not any(needle in a.replace('\\','/').casefold() for a in args)
with (task/'execution-log.md').open('a',encoding='utf-8') as log:
    log.write('\nGREEN: experience-preflight -> PASS（Git推送工作副本收尾）；精确路径、目标fb88105a、远端同哈希、干净状态、无使用进程已核实；仅合法已提交源文件缓存，未构建、未启动应用、未产生新提交。仅正常Git删除本任务checkout，保留分支及其他worktree。\n')
r=subprocess.run(['git','-c','core.longpaths=true','-C',repo,'worktree','remove',str(target)],capture_output=True,timeout=600)
assert r.returncode==0
assert not os.path.lexists(target)
assert needle not in git(repo,'worktree','list','--porcelain').decode().casefold()
assert git(repo,'rev-parse',branch).decode().strip()==commit
result=dict(status='PASS',time=datetime.now().astimezone().isoformat(),path=str(target),branch=branch,commit=commit,
    producedNewCommits=False,buildPerformed=False,applicationStarted=False,physicalPathExists=False,registeredAfter=False,
    gitRemovalExitCode=r.returncode,branchPreserved=True,ignoredCaches=len(ignored))
(task/'worktree-closeout.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
