from pathlib import Path
import json,os,subprocess
repo=Path(__file__).resolve().parents[3]
files=['ops/spug/release-center/'+name for name in ('backend_patch_agent.py','backend_patch_build.py','backend_patch_contract.py','test_backend_patch_runtime_boundary.py','test_ui_backend_patch.cjs','ui/backend-patch.js')]+['docs/experience-index.md','docs/release-agent-checklist.md']
env=dict(os.environ,PYTHONUTF8='1');env['PATH']='C:/Users/D01021/Documents/spug-handoff-work-20261030/runtime/Python312-3.12.14;'+env['PATH']
def run(*args):
    result=subprocess.run(['git',*args],cwd=repo,env=env,capture_output=True);assert result.returncode==0,'Git step failed: '+args[0]
    return result.stdout.decode('utf-8').strip()
assert not run('diff','--cached','--name-only');run('diff','--check')
run('add','--',*files);assert sorted(run('diff','--cached','--name-only').splitlines())==sorted(files)
log=Path('C:/SpugHandoff/release/private/backend-patch-full-release-20261102/runtime-boundary-commit.private.log');assert not log.exists()
with log.open('wb') as out:r=subprocess.run(['git','commit','-m','任务: 后端补丁只读验收后恢复正常运行'],cwd=repo,env=env,stdout=out,stderr=subprocess.STDOUT)
assert r.returncode==0,'Commit rejected; inspect private hook output'
print(json.dumps(dict(commit=run('rev-parse','HEAD'),files=run('show','--pretty=','--name-only','HEAD').splitlines())))
