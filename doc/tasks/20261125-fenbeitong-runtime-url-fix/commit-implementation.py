"""Commit only the reviewed task files in both isolated repositories."""
import json
import os
from pathlib import Path
import subprocess
import sys

TASK=Path(__file__).resolve().parent
SOURCE=Path('C:/SpugHandoff/release/fenbeitong-runtime-url-20261125')
MAINT=Path('C:/SpugHandoff/release/fenbeitong-runtime-url-maint-20261125')

def git(root,*args):
    env=dict(os.environ)
    env['PATH']=str(Path(sys.executable).parent)+';C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell;'+env['PATH']
    env['PYTHONUTF8']='1'
    result=subprocess.run(['git','-C',str(root),*args],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    if result.returncode:
        print(result.stdout.decode('utf-8',errors='replace')[-5000:],flush=True)
        raise RuntimeError('Git command failed: '+str(result.returncode))
    return result.stdout

java='IntRuoyiBackend/yudao-module-system/src/'
package='cn/iocoder/yudao/module/system/'
files=[java+'main/java/'+package+'controller/admin/auth/vo/AuthFenbeitongAssistantStatusRespVO.java',
       java+'main/java/'+package+'service/fenbeitongassistant/FenbeitongAssistantProperties.java',
       java+'main/java/'+package+'service/fenbeitongassistant/FenbeitongAssistantServiceImpl.java',
       java+'test/java/'+package+'service/fenbeitongassistant/FenbeitongAssistantServiceImplTest.java',
       'IntRuoyiBackend/yudao-server/src/main/resources/application-local.yaml',
       'IntRuoyiFronted/.env.prod','IntRuoyiFronted/.env.test',
       'IntRuoyiFronted/src/api/login/index.ts',
       'IntRuoyiFronted/src/views/erp/finance/fenbeitong-voucher/index.vue',
       'IntRuoyiFronted/tests/e2e/fenbeitong-assistant-static.spec.cjs',
       'IntRuoyiFronted/types/env.d.ts','IntRuoyiFronted/tests/fenbeitong-runtime-url.behavior.spec.cjs']
maintenance=['docs/experience-index.md','ops/spug/release-center/README.md',
             'ops/spug/release-center/intruoyi_runtime_agent.py',
             'ops/spug/release-center/invoice-print-runtime-config.md',
             'ops/spug/release-center/test_fenbeitong_integration_config.py',
             'ops/spug/release-center/test_fenbeitong_runtime_url.py']
records={}
for name,root,paths,message in [('source',SOURCE,files,'fix: 修复分贝通运行时地址接入'),
        ('maintenance',MAINT,maintenance,'任务: 补齐分贝通发布地址配置契约')]:
    assert git(root,'branch','--show-current').strip()==b'codex/fenbeitong-runtime-url-20261125'
    staged=set(git(root,'diff','--cached','--name-only','-z').decode('utf-8').strip('\0').split('\0'))-{''}
    assert not staged or staged==set(paths), 'Unrelated staged changes; preserve and stop'
    for path in paths:
        (root/path).read_bytes().decode('utf-8',errors='strict')
    git(root,'add','--',*paths)
    git(root,'diff','--cached','--check')
    actual=set(git(root,'diff','--cached','--name-only','-z').decode('utf-8').strip('\0').split('\0'))
    assert actual==set(paths)
    print(name,git(root,'diff','--cached','--stat').decode(),flush=True)
    output=git(root,'commit','-m',message)
    sha=git(root,'rev-parse','HEAD').decode().strip()
    assert set(git(root,'diff-tree','--no-commit-id','--name-only','-r',sha).decode().splitlines())==set(paths)
    assert not git(root,'status','--porcelain','--untracked-files=all').strip()
    records[name]={'commit':sha,'files':paths}
    (TASK/'implementation-commits.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(name,'PASS',sha,output.decode('utf-8',errors='replace')[-1600:],flush=True)
