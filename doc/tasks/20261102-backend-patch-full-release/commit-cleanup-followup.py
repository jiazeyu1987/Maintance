from pathlib import Path
import json,os,subprocess,sys
repo=Path(__file__).resolve().parents[3]
files=['ops/spug/release-center/'+name for name in ('artifact_files.py','runtime_resource_cleanup.py','test_runtime_resource_cleanup.py')]+['docs/experience-index.md','docs/release-agent-checklist.md']
legacy=len(sys.argv)>1 and sys.argv[1]=='legacy'
if legacy:files.remove('ops/spug/release-center/artifact_files.py')
env=dict(os.environ,PYTHONUTF8='1');env['PATH']='C:/Users/D01021/Documents/spug-handoff-work-20261030/runtime/Python312-3.12.14;'+env['PATH']
def run(*args):
    result=subprocess.run(['git',*args],cwd=repo,env=env,capture_output=True)
    assert result.returncode==0,'Git step failed: '+args[0]
    return result.stdout.decode('utf-8').strip()
assert not run('diff','--cached','--name-only');run('diff','--check')
run('add','--',*files);assert sorted(run('diff','--cached','--name-only').splitlines())==sorted(files)
log=Path('C:/SpugHandoff/release/private/backend-patch-full-release-20261102/'+('cleanup-legacy' if legacy else 'cleanup-followup')+'-commit.private.log');assert not log.exists()
message='任务: 保留缺少历史清单的旧资源组' if legacy else '任务: 稳定旧资源身份并保留不明恢复资料'
with log.open('wb') as out:r=subprocess.run(['git','commit','-m',message],cwd=repo,env=env,stdout=out,stderr=subprocess.STDOUT)
assert r.returncode==0,'Commit rejected; inspect private hook output'
print(json.dumps(dict(commit=run('rev-parse','HEAD'),files=run('show','--pretty=','--name-only','HEAD').splitlines())))
