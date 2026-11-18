"""Commit the verified build metadata change with only owned implementation files."""
from pathlib import Path
import json,os,subprocess
repo=Path(__file__).resolve().parents[3]
files=['ops/spug/release-center/'+name for name in ('backend_patch_agent.py','test_backend_patch_untouched_restore.py')]
env=dict(os.environ,PYTHONUTF8='1')
env['PATH']='C:/Users/D01021/Documents/spug-handoff-work-20261030/runtime/Python312-3.12.14;'+env['PATH']
def run(*args):
    r=subprocess.run(['git',*args],cwd=repo,env=env,capture_output=True)
    assert r.returncode==0,'Git step failed: '+args[0]
    return r.stdout.decode('utf-8').strip()
assert run('diff','--cached','--name-only')==''
run('diff','--check','--',*files)
p=Path(__file__).with_name('execution-log.md');s=p.read_text('utf-8')
s+='\n- RED: 未开始切换恢复4项用例产生8条含子场景错误，缺deployment.json路径和worker核验入口。首次回归命令误列不存在test_operation_journal，未记PASS。GREEN/REGRESSION: python -X utf8 -m unittest test_backend_patch_untouched_restore test_backend_patch test_interruption test_intruoyi_runtime test_frontend_patch -> 92项PASS；严格验证未开始切换原程序，缺证据/活跃worker/漂移/保护/未知文件均拒绝，无数据库或容器变更。\n'
p.write_text(s,encoding='utf-8')
run('add','--',*files)
assert sorted(run('diff','--cached','--name-only').splitlines())==sorted(files)
log=Path('C:/SpugHandoff/release/private/backend-patch-full-release-20261102/untouched-restore-commit.private.log')
assert not log.exists()
with log.open('wb') as out:
    r=subprocess.run(['git','commit','-m','修复: 未开始切换时严格核验原程序'],cwd=repo,env=env,stdout=out,stderr=subprocess.STDOUT)
assert r.returncode==0,'Commit rejected; inspect private hook log'
print(json.dumps(dict(commit=run('rev-parse','HEAD'),files=run('show','--pretty=','--name-only','HEAD').splitlines()),ensure_ascii=True))
