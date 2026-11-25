"""Read actual helper source into private evidence; print paths only."""
import json, subprocess, sys
from pathlib import Path
base=Path('C:/SpugHandoff/release')
private=base/'private/intruoyi-fenbeitong-test-prod-20261125'
sys.path.insert(0,str(base/'source/ops/spug/release-center'))
from intruoyi_runtime import Runtime,ssh_source_bytes
r=Runtime(json.loads((base/'executor.private.json').read_bytes()))
env=sys.argv[1]; assert env in ('test','prod')
p=r.profile(env)
node=r"""const fs=require('fs');const files=[];
function walk(d){for(const e of fs.readdirSync(d,{withFileTypes:true})){
if(['node_modules','data','.git','logs','config'].includes(e.name))continue;
const path=d+'/'+e.name;if(e.isDirectory())walk(path);else if(/\.(js|cjs|mjs|ts)$/.test(path)){
const source=fs.readFileSync(path,'utf8');if(source.includes('configuration is missing')||source.includes('fenbeitong-expense-reimbursement/config')||source.includes('api.getConfig')||path.endsWith('/routes.js')||path.endsWith('/storage.js'))files.push({path,source});}}}
walk('/app');console.log(JSON.stringify(files));"""
code='import json,subprocess\nnode='+repr(node)+'\nprint(subprocess.check_output(["docker","exec","fenbeitong-assistant","node","-e",node]).decode())\n'
q=subprocess.run(['ssh',*r.ssh_options(),'root@'+p['host'],p['python']+' -'],input=ssh_source_bytes(code),capture_output=True,timeout=45)
assert q.returncode==0,'Read-only source probe failed'
files=json.loads(q.stdout)
(private/(env+'-helper-config-source.private.json')).write_text(json.dumps(files,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(environment=env,files=[x['path'] for x in files])))
