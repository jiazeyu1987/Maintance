import json,sys
from pathlib import Path
task=Path(__file__).resolve().parent
root=Path('C:/SpugHandoff/release/private/intruoyi-fenbeitong-test-prod-20261125')
env,tag,commit=sys.argv[1:]; assert env in ('test','prod')
page_env='test' if env=='test' else 'prod-maintenance'
report=json.loads((task/(page_env+'-page-acceptance.json')).read_text(encoding='utf-8'))
assert report['status'] in ('PASS','PASS_WITH_OBSERVATIONS') and not report['blockers']
assert report['releaseTag']==tag and report['sourceCommit']==commit
if env=='test':
    runtime=json.loads((root/'test-runtime-verification.json').read_text(encoding='utf-8'))
    assert runtime['status']=='PASS' and runtime['releaseTag']==tag and runtime['gitCommit']==commit
    action='mark-tested'
else:action='accept-prod'
note='真实前端登录、排产菜单实际列表响应、分贝通本服状态地址/票据/认证iframe及可见版本说明均通过；全部观察项逐条核对为非阻断，范围与原始证据见本任务页面验收报告。不代表凭证同步、记账写入或完整业务E2E。'
payload=dict(releaseTag=tag,requestId='intruoyi-fbt-'+tag+'-'+action+'-1',note=note)
(root/(action+'.json')).write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
print(json.dumps(dict(action=action,releaseTag=tag,prerequisite=report['status']),ensure_ascii=False))
