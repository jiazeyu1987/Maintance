"""Commit only the verified Quartz same-definition fix, no task/private files."""
from pathlib import Path
import json, os, subprocess
repo=Path('C:/SpugHandoff/backend-log-src-20261102')
files=[
 'IntRuoyiBackend/yudao-framework/yudao-spring-boot-starter-job/src/main/java/cn/iocoder/yudao/framework/quartz/core/scheduler/SchedulerManager.java',
 'IntRuoyiBackend/yudao-framework/yudao-spring-boot-starter-job/src/test/java/cn/iocoder/yudao/framework/quartz/core/scheduler/SchedulerManagerDefinitionTest.java',
 'IntRuoyiBackend/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/job/JobServiceImpl.java',
 'IntRuoyiBackend/yudao-module-infra/src/test/java/cn/iocoder/yudao/module/infra/service/job/JobStartupDefinitionSyncTest.java']
env=dict(os.environ,PYTHONUTF8='1')
env['PATH']='C:/Users/D01021/Documents/spug-handoff-work-20261030/runtime/Python312-3.12.14;'+env['PATH']
def run(*args):
    r=subprocess.run(['git',*args],cwd=repo,env=env,capture_output=True)
    assert r.returncode==0,'Git step failed: '+args[0]
    return r.stdout.decode('utf-8').strip()
assert not run('diff','--cached','--name-only')
run('diff','--check')
note='\n- GREEN/REGRESSION: Maven Quartz definition/startup + existing infra/maintenance/job tests -> PASS，63项，0失败/错误/跳过；真实内存Quartz保留原start/next fire时间。当前未修改三服Quartz配置或放宽只读保护。\n'
for folder in [Path(__file__).parent,repo/'doc/tasks/20261102-backend-patch-startup-noop']:
    path=folder/'execution-log.md';text=path.read_text('utf-8')+note;path.write_text(text,encoding='utf-8');assert path.read_text('utf-8')==text
run('add','--',*files)
assert sorted(run('diff','--cached','--name-only').splitlines())==sorted(files)
log=Path('C:/SpugHandoff/release/private/backend-patch-full-release-20261102/quartz-commit.private.log');assert not log.exists()
with log.open('wb') as output:r=subprocess.run(['git','commit','-m','任务: Quartz定义一致时避免启动重复写入'],cwd=repo,env=env,stdout=output,stderr=subprocess.STDOUT)
assert r.returncode==0,'Commit rejected; inspect private hook log'
commit=run('rev-parse','HEAD')
record=Path(__file__).with_name('selected-release.json')
previous=json.loads(record.read_text('utf-8'))
history=Path(__file__).with_name('selection-before-quartz.json');assert not history.exists()
history.write_text(json.dumps(previous,indent=2)+'\n',encoding='utf-8')
record.write_text(json.dumps(dict(commit=commit),indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(commit=commit,files=run('show','--pretty=','--name-only','HEAD').splitlines(),remaining=run('status','--short'))))
