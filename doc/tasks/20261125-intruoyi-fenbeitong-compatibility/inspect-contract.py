"""Read-only runtime contract inventory. No login or business operations."""
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shlex
import subprocess

TASK = Path(__file__).resolve().parent
CONFIG = Path('C:/SpugHandoff/release/executor.private.json')
REMOTE = r'''
import json,re,subprocess,datetime
TARGET=__TARGET__
def run(args):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=35)
 if p.returncode: raise RuntimeError('READ_FAILED_'+str(p.returncode))
 return p.stdout.decode('utf-8')
def inspect(name): return json.loads(run(['docker','inspect',name]))[0]
assistant=inspect('fenbeitong-assistant')
if assistant['Config'].get('Labels',{}).get('release.application')!='fenbeitong': raise RuntimeError('APPLICATION_IDENTITY_MISMATCH')
out={'observedAtUtc':datetime.datetime.utcnow().isoformat()+'Z','containers':{}}
for role,name in [('backend',TARGET['targetBackend']),('frontend',TARGET['targetFrontend']),('assistant','fenbeitong-assistant')]:
 c=inspect(name)
 env=dict(s.split('=',1) for s in c['Config'].get('Env',[]) if '=' in s)
 text=' '.join([env.get('JAVA_OPTS',''),env.get('JAVA_TOOL_OPTIONS',''),*c['Config'].get('Cmd',[])])
 matches=re.findall(r'(?:--|-D)yudao\.erp\.fenbeitong-assistant\.([a-z-]+)=([^\s]+)',text)
 safe={k:v for k,v in matches if k in ['assistant-host','assistant-port']}
 safe.update({k:env[k] for k in ['FENBEITONG_ASSISTANT_TICKET_VALIDATE_URL','FENBEITONG_ASSISTANT_HOST','SCHEDULER_ENABLED','PAYMENT_STATUS_SYNC_ENABLED'] if k in env})
 out['containers'][role]={'name':name,'image':c['Config']['Image'],'imageId':c['Image'],'running':c['State']['Running'],'settings':safe,'networks':list(c['NetworkSettings']['Networks'])}
node=r"""
const fs=require('fs'),path=require('path');
function walk(p){return fs.readdirSync(p,{withFileTypes:true}).flatMap(x=>x.isDirectory()?walk(path.join(p,x.name)):[path.join(p,x.name)]);}
const files=walk('/app/backend/src').filter(p=>/auth|permission|ticket|session/i.test(p));
const contract=files.flatMap(p=>fs.readFileSync(p,'utf8').split('\n').flatMap((s,i)=>/normalizeAssistantKingdeeConfig|required|baseUrl|acctId|username|password|appId|signedData|timestamp|lcid/.test(s)?[{file:p,line:i+1,text:s}]:[]));
const server=fs.readFileSync('/app/server.js','utf8').split('\n');
const lines=server.flatMap((s,i)=>/auth|ticket|permission|session|callback/i.test(s)||i>=122&&i<=154?[{line:i+1,text:s}]:[]);
(async()=>{
 const base=new URL(process.env.FENBEITONG_ASSISTANT_TICKET_VALIDATE_URL);
 const checks=[];
 for(const p of ['/actuator/health',base.pathname]){
  const u=new URL(p,base),r=await fetch(u,{method:'GET',signal:AbortSignal.timeout(8000)});
  checks.push({path:p,status:r.status});
 }
 process.stdout.write(JSON.stringify({files,serverContractLines:lines,kingdeeContract:contract,backendConnectivity:checks}));
})().catch(()=>{process.exitCode=1;});
"""
out['assistantSource']=json.loads(run(['docker','exec','fenbeitong-assistant','node','-e',node]))
frontend=r"""
import os,re,json
roots=['/usr/share/nginx/html']
hits=[]
sources={}
for root in roots:
 for folder,dirs,files in os.walk(root):
  for name in files:
   if name.endswith(('.js','.html')):
    p=os.path.join(folder,name)
    if os.path.getsize(p)>20000000: continue
    text=open(p,encoding='utf-8').read()
    sources[name]=text
    if 'fenbeitong-assistant-ticket' in text or 'ErpFenbeitongVoucher' in text:
     pos=text.find('auth/callback')
     hits.append({'file':p,'assistantUrls':sorted(set(re.findall(r'http://[0-9.]+:18734/?',text))),'hasTicketEndpoint':'fenbeitong-assistant-ticket' in text,'hasCallback':pos>=0,'hasStatus':'fenbeitong-assistant/status' in text,'callbackContext':text[max(0,pos-400):pos+200] if pos>=0 else ''})
configs=[]
for path in ['/etc/nginx/conf.d/default.conf','/etc/nginx/nginx.conf']:
 p=roots[0].split('/usr/share/nginx/html')[0]+path
 if os.path.isfile(p):
  ls=open(p,encoding='utf-8').read().splitlines()
  configs.extend({'file':path,'line':i+1,'text':'\n'.join(ls[max(0,i-1):i+7])} for i,s in enumerate(ls) if 'fenbeitong' in s)
entry=open(os.path.join(roots[0],'index.html'),encoding='utf-8').read()
entry_files=re.findall(r'assets/([^"<>/\s]+\.js)',entry)
for hit in hits:
 if not hit.get('hasCallback'): continue
 child=os.path.basename(hit['file']); visited={child}; queue=[(child,[child])]; chain=None
 while queue and chain is None:
  name,trail=queue.pop(0)
  if name in entry_files: chain=list(reversed(trail));break
  for parent,text in sources.items():
   if parent not in visited and name in text:
    visited.add(parent);queue.append((parent,trail+[parent]))
 hit['currentIndexDependencyChain']=chain
hits.append({'nginxAssistantConfig':configs,'entryScripts':entry_files})
print(json.dumps(hits))
"""
# The nginx image has no Python. Host reads only the registered frontend's web assets through proc root.
front=inspect(TARGET['targetFrontend']); pid=front['State']['Pid']
frontend=frontend.replace("roots=['/usr/share/nginx/html']", "roots=['/proc/%d/root/usr/share/nginx/html']"%pid)
ns={};exec(compile(frontend,'<frontend-assets>','exec'),ns)
# A separate marker is used so the caller can parse the final record after asset inventory.
print('CONTRACT_RESULT='+json.dumps(out,ensure_ascii=False))
'''

def observe(item):
    key, target = item
    config = json.loads(CONFIG.read_text(encoding='utf-8-sig'))
    safe_target = {'targetBackend':target['backend'],'targetFrontend':target['frontend']}
    source = REMOTE.replace('__TARGET__', repr(safe_target))
    encoded = base64.b64encode(source.encode()).decode()
    command = 'import base64;exec(compile(base64.b64decode(%r),"<contract-readonly>","exec"))' % encoded
    args = ['ssh','-i',config['sshIdentityFile'],'-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+config['sshKnownHostsFile'],'-o','ConnectTimeout=10','root@'+target['host'],target.get('python','python3')+' -c '+shlex.quote(command)]
    result = subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=90)
    if result.returncode:
        raise RuntimeError(key+': remote read failed '+str(result.returncode))
    lines = result.stdout.decode('utf-8').splitlines()
    data = json.loads(next(s.removeprefix('CONTRACT_RESULT=') for s in lines if s.startswith('CONTRACT_RESULT=')))
    data['frontendAssets'] = json.loads(lines[0])
    return key,data

if __name__ == '__main__':
    config = json.loads(CONFIG.read_text(encoding='utf-8-sig'))
    selected = [(k,config['targets'][k]) for k in ['test','prod']]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = dict(pool.map(observe,selected))
    (TASK/'contract-inventory.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for key,data in results.items():
        print(key,json.dumps({'observedAtUtc':data['observedAtUtc'],'frontendAssets':data['frontendAssets'],'kingdeeContract':data['assistantSource']['kingdeeContract'],'connectivity':data['assistantSource']['backendConnectivity']},ensure_ascii=False))
