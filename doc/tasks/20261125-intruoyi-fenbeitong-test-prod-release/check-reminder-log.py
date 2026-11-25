"""Read-only classify the separately observed scheduled-job configuration error."""
import json,subprocess,sys
from pathlib import Path
base=Path('C:/SpugHandoff/release'); out=base/'private/intruoyi-fenbeitong-test-prod-20261125'
sys.path.insert(0,str(base/'source/ops/spug/release-center'))
from intruoyi_runtime import Runtime,ssh_source_bytes
r=Runtime(json.loads((base/'executor.private.json').read_bytes()))
env=sys.argv[1]; assert env in ('test','prod'); p=r.profile(env)
code='p='+repr(p)+'\n'+r'''
import json,subprocess,re
q=subprocess.run(['docker','logs','--since','1h',p['backend']],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
raw=(q.stdout+q.stderr).decode('utf-8','replace')
marker='注册证提醒任务执行失败'
lines=[x for x in raw.splitlines() if marker in x]
print(json.dumps(dict(backend=p['backend'],matchCount=len(lines),lines=lines,tenantIds=sorted(set(re.findall(r'tenantId=(\d+)', '\n'.join(lines)))),missingConfig=any('注册证配置中设置注册证负责人' in x for x in lines))))
'''
q=subprocess.run(['ssh',*r.ssh_options(),'root@'+p['host'],p['python']+' -'],input=ssh_source_bytes(code),capture_output=True,timeout=35)
assert q.returncode==0
v=json.loads(q.stdout);(out/(env+'-reminder-log.private.json')).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v[k] for k in ('backend','matchCount','tenantIds','missingConfig')},ensure_ascii=False))
