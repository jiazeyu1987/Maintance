"""Commit the verified build metadata change with only owned implementation files."""
from pathlib import Path
import json,os,subprocess
repo=Path(__file__).resolve().parents[3]
files=['ops/spug/release-center/'+name for name in ('intruoyi_build.py','test_release_info_changes.py','test_build_recurrence_guards.py')]
env=dict(os.environ,PYTHONUTF8='1')
env['PATH']='C:/Users/D01021/Documents/spug-handoff-work-20261030/runtime/Python312-3.12.14;'+env['PATH']
def run(*args):
    r=subprocess.run(['git',*args],cwd=repo,env=env,capture_output=True)
    assert r.returncode==0,'Git step failed: '+args[0]
    return r.stdout.decode('utf-8').strip()
assert run('diff','--cached','--name-only')==''
run('diff','--check','--',*files)
p=Path(__file__).with_name('execution-log.md');s=p.read_text('utf-8')
s+='\n- GREEN/REGRESSION: python -X utf8 -m unittest test_release_info_changes test_intruoyi_build test_build_recurrence_guards -> 35项PASS；真实临时Git验证目标绑定、UTF-8中文说明、最多10条及缺目标失败。构建器为前后端使用同一release-info内容；无空说明降级。\n'
p.write_text(s,encoding='utf-8')
run('add','--',*files)
assert sorted(run('diff','--cached','--name-only').splitlines())==sorted(files)
log=Path('C:/SpugHandoff/release/private/backend-patch-full-release-20261102/release-info-commit.private.log')
assert not log.exists()
with log.open('wb') as out:
    r=subprocess.run(['git','commit','-m','修复: 全量发布生成固定提交版本说明'],cwd=repo,env=env,stdout=out,stderr=subprocess.STDOUT)
assert r.returncode==0,'Commit rejected; inspect private hook log'
print(json.dumps(dict(commit=run('rev-parse','HEAD'),files=run('show','--pretty=','--name-only','HEAD').splitlines()),ensure_ascii=True))
