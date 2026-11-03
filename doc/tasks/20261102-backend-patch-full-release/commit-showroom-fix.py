"""Commit only the approved, verified startup fix; keep raw hook output private."""
from pathlib import Path
import json,os,subprocess
repo=Path('C:/SpugHandoff/backend-log-src-20261102')
files=[
 'IntRuoyiBackend/yudao-module-showroom/src/main/java/cn/iocoder/yudao/module/showroom/cover/ShowroomProductCoverBatchTaskService.java',
 'IntRuoyiBackend/yudao-module-showroom/src/test/java/cn/iocoder/yudao/module/showroom/cover/ShowroomProductCoverStartupRecoveryTest.java']
env=dict(os.environ,PYTHONUTF8='1')
env['PATH']='C:/Users/D01021/Documents/spug-handoff-work-20261030/runtime/Python312-3.12.14;'+env['PATH']
def run(*args):
    r=subprocess.run(['git',*args],cwd=repo,env=env,capture_output=True)
    assert r.returncode==0,'Git step failed: '+args[0]
    return r.stdout.decode('utf-8').strip()
assert run('diff','--cached','--name-only')==''
run('diff','--check')
for folder in [Path(__file__).parent,repo/'doc/tasks/20261102-backend-patch-startup-noop']:
    p=folder/'execution-log.md';s=p.read_text('utf-8')
    s+='\n- GREEN/REGRESSION: Maven -pl yudao-module-showroom -am -Dtest=ShowroomProductCoverStartupRecoveryTest,ShowroomProductCoverBatchTaskServiceTest -Dsurefire.failIfNoSpecifiedTests=false test -> PASS；新增6项、既有9项，共15项，0失败/错误/跳过，BUILD SUCCESS。无候选不写、真实恢复保留、异常继续传播。\n'
    p.write_text(s,encoding='utf-8');assert p.read_text('utf-8')==s
run('add','--',*files)
assert sorted(run('diff','--cached','--name-only').splitlines())==sorted(files)
log=Path('C:/SpugHandoff/release/private/backend-patch-full-release-20261102/showroom-commit.private.log')
assert not log.exists()
with log.open('wb') as out:
    r=subprocess.run(['git','commit','-m','任务: 展厅启动无恢复工作时仅查询'],cwd=repo,env=env,stdout=out,stderr=subprocess.STDOUT)
assert r.returncode==0,'Commit rejected; inspect private hook log'
print(json.dumps(dict(commit=run('rev-parse','HEAD'),files=run('show','--pretty=','--name-only','HEAD').splitlines(),remaining=run('status','--short')),ensure_ascii=True))
