import json
import os
import subprocess
from pathlib import Path

base=Path('C:/SpugHandoff/release')
out=base/'private/intruoyi-fenbeitong-test-prod-20261125'
work=base/'registration-config-release-fix-20261126'
main=Path('C:/Users/D01021/Documents/ChatGPT/IntRuoyi')
files=['IntRuoyiBackend/sql/mysql/release-sources.json','IntRuoyiBackend/sql/mysql/target-preflight/20261125_registration_certificate_config_menu_parent.preflight.sql']
env=dict(os.environ)
env['PATH']='C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python;C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell;'+env['PATH']
env['PYTHONUTF8']='1'
def git(root,*args):
    result=subprocess.run(['git','-c','core.longpaths=true','-C',str(root),*args],env=env,capture_output=True)
    if result.returncode:
        (out/'integration-error.private.log').write_bytes(result.stdout+result.stderr)
        raise RuntimeError('Git integration failed; exact private diagnostic retained')
    return result.stdout
assert git(main,'rev-parse','HEAD').decode().strip()=='e1ccafbc6638e64f544e609f9072096f529e45b2','Main advanced; inspect first'
before=git(main,'status','--porcelain','--untracked-files=no')
assert not git(work,'diff','--cached','--name-only').strip()
git(work,'add','--',*files)
assert set(git(work,'diff','--cached','--name-only').decode().splitlines())==set(files)
log=git(work,'commit','-m','任务: 补齐注册证配置菜单发布登记和预检')
(out/'source-commit.private.log').write_bytes(log)
commit=git(work,'rev-parse','HEAD').decode().strip()
assert not git(work,'status','--porcelain','--untracked-files=all').strip()
assert git(main,'status','--porcelain','--untracked-files=no')==before
git(main,'merge','--ff-only',commit)
assert git(main,'status','--porcelain','--untracked-files=no')==before
assert all(git(main,'show','HEAD:'+name)==git(work,'show','HEAD:'+name) for name in files)
report=dict(status='PASS',commit=commit,files=files,mainMerged=True,unrelatedChangesPreserved=True,worktree=str(work),newCommit=True)
(out/'source-integration.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
(out/'build-r2.json').write_text(json.dumps(dict(requestId='intruoyi-fenbeitong-20261126-build-2',commit=commit)),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
