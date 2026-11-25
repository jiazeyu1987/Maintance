"""Read-only helper/backend connectivity evidence, never print environment secrets."""
import json
import subprocess
import sys
from pathlib import Path
base=Path('C:/SpugHandoff/release'); out=base/'private/intruoyi-fenbeitong-test-prod-20261125'
sys.path.insert(0,str(base/'source/ops/spug/release-center'))
from intruoyi_runtime import Runtime,ssh_source_bytes
r=Runtime(json.loads((base/'executor.private.json').read_bytes()))
env=sys.argv[1]; assert env in ('test','prod'); p=r.profile(env)
page=json.loads((out/env/'fenbeitong-page.private.json').read_text(encoding='utf-8'))
code='p='+repr(p)+'\nstart='+repr(page['startedAt'])+'\nend='+repr(page['endedAt'])+'\n'+'''
import json,subprocess
def inspect(name):return json.loads(subprocess.check_output(['docker','inspect',name]))[0]
helper=inspect('fenbeitong-assistant'); backend=inspect(p['backend'])
values=dict(v.split('=',1) for v in helper['Config']['Env'])
url=values.get('FENBEITONG_ASSISTANT_TICKET_VALIDATE_URL')
node="""const fs=require('fs'),dns=require('dns').promises;
const url=process.env.FENBEITONG_ASSISTANT_TICKET_VALIDATE_URL;
(async()=>{let dnsResult;try{dnsResult=await dns.lookup(new URL(url).hostname,{all:true})}catch(e){dnsResult={error:e.code}};
let http;try{const r=await fetch(new URL('/actuator/health',url),{signal:AbortSignal.timeout(10000)});http={status:r.status,body:await r.text()}}catch(e){http={error:e.message,cause:e.cause?.code}};
const files=[];const walk=d=>{for(const item of fs.readdirSync(d,{withFileTypes:true})){if(['node_modules','.git','data'].includes(item.name))continue;const path=d+'/'+item.name;if(item.isDirectory())walk(path);else if(/\\.(js|cjs|mjs|ts)$/.test(path)){try{const x=fs.readFileSync(path,'utf8');if(x.includes('/auth/callback')||x.includes('FENBEITONG_ASSISTANT_TICKET_VALIDATE_URL'))files.push({path,source:x})}catch(e){}}}};walk('/app');
console.log(JSON.stringify({dnsResult,http,files}));})();"""
probe=json.loads(subprocess.check_output(['docker','exec','fenbeitong-assistant','node','-e',node]))
logs=subprocess.run(['docker','logs','--tail','120','fenbeitong-assistant'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
backend_logs=subprocess.run(['docker','logs','--since',start,'--until',end,p['backend']],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
print(json.dumps(dict(helper=dict(image=helper['Image'],state=helper['State'],networks=helper['NetworkSettings']['Networks'],ticketValidateUrl=url),
backend=dict(image=backend['Image'],networks=backend['NetworkSettings']['Networks']),probe=probe,logs=(logs.stdout+logs.stderr).decode('utf-8','replace'),backendLogs=(backend_logs.stdout+backend_logs.stderr).decode('utf-8','replace'))))
'''
q=subprocess.run(['ssh',*r.ssh_options(),'root@'+p['host'],p['python']+' -'],input=ssh_source_bytes(code),capture_output=True,timeout=55)
(out/(env+'-helper-probe-stderr.private.txt')).write_bytes(q.stderr)
assert q.returncode==0,'Read-only helper inspection failed'
v=json.loads(q.stdout); (out/(env+'-helper-connectivity.private.json')).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(environment=env,helperImage=v['helper']['image'],ticketValidateUrl=v['helper']['ticketValidateUrl'],
    helperNetworks=list(v['helper']['networks']),backendNetworks=list(v['backend']['networks']),
    dns=v['probe']['dnsResult'],health=v['probe']['http'],sourceFiles=[x['path'] for x in v['probe']['files']]),ensure_ascii=False))
