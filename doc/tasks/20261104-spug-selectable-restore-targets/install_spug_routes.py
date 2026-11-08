"""Compare current local configuration, publish two admitted routes, reload own entry only."""
import argparse,ast,copy,hashlib,json,os,subprocess
from pathlib import Path
from install_controls import PRIVATE,ROOTS

CONTAINER='intruoyi-spug-transfer-spug-1'
RUNTIME=Path('C:/Spug/runtime')
APP='intruoyi-57-safe-20261024-v1'
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def sha(v):return hashlib.sha256(canonical(v)).hexdigest()
def docker(code,payload=None):
 p=subprocess.run(['docker','exec','-i',CONTAINER,'python3','-B','-c',code],input=None if payload is None else canonical(payload),capture_output=True)
 if p.returncode:
  (PRIVATE/'spug-route-error.private.log').write_bytes(p.stdout+p.stderr);raise RuntimeError('SPUG_ROUTE_COMMAND_FAILED')
 return json.loads(p.stdout)
def prepare():
 before=json.loads((PRIVATE/'spug-before.private.json').read_text(encoding='utf-8'))
 simple=copy.deepcopy(before['smallapp-simple-settings.json']);entry=copy.deepcopy(before['smallapp-entry-settings.json']);bridge=copy.deepcopy(before['smallapp-bridge.private.json'])
 binding=next(b for b in simple['bindings'] if b['applicationId']==APP)
 app=next(a for a in entry['applications'] if a['applicationId']==APP)
 template=before[bridge['sourceConnections'][APP]]
 files={};receipts=[]
 for suffix in ('58','59'):
  host='172.30.30.'+suffix;ref='intruoyi-main-'+suffix+'-safe-restore-20261104-v1'
  receipt=json.loads((PRIVATE/(host+'-target-installation.json')).read_text(encoding='utf-8'))
  assert receipt['targetConfigRef']==ref and receipt['root']==ROOTS[suffix] and not receipt['restorePerformed']
  preflight=json.loads((PRIVATE/(host+'-authenticated-selections.json')).read_text(encoding='utf-8'))
  rows=[r for r in preflight['applications'] if r['applicationId']==APP]
  assert len(rows)==1 and ref in rows[0]['freshTargetConfigRefs'],'LIVE_TARGET_ADMISSION_REQUIRED'
  binding['overwriteTargetServers'][host]=ref
  route=copy.deepcopy(next(r for r in binding['restoreProgressBindings'].values() if r['server']==host))
  route['progressRoot']=ROOTS[suffix]
  if suffix=='58':route['pythonPath']='/usr/local/libexec/spug-main-restore-20261104/python/bin/python3.12'
  binding['restoreProgressBindings'][ref]=route
  assert route['sshTransport']=={'host':'host.docker.internal','port':18500+int(suffix)}
  if ref not in app['targetConfigRefs']:app['targetConfigRefs'].append(ref)
  config=copy.deepcopy(template);origin='http://host.docker.internal:'+('43658' if suffix=='58' else '33659')
  config.update(submitUrl=origin+'/operations',queryUrlTemplate=origin+'/operations/{operationId}',selectionUrl=origin+'/selections',
   sourceConfigRefs=[APP],targetConfigRefs=[ref],selectedTargetPreflight=True,credentialRef='main-restore-'+suffix+'-headers-20261104.private.json',registrationBindings=[])
  filename='main-restore-'+suffix+'-bridge-20261104.private.json';bridge['targetConnections'][ref]=filename
  files[filename]=config;files[config['credentialRef']]=json.loads((PRIVATE/(host+'-control-headers.private.json')).read_text(encoding='utf-8'))
  receipts.append(receipt)
 # This records the explicit local display registration; destination controls each
 # publish their independent authenticated registration for their one allowed target.
 registration={'schemaVersion':'ApplicationRegistration/v1','applicationId':APP,'sourceConfigRef':APP,
  'displayName':'IntRuoyi 正式服备份','allowedRestoreTargets':[{'configRef':binding['overwriteTargetServers'][h]} for h in sorted(binding['overwriteTargetServers'])]}
 app['registrationSha256']=sha(registration)
 plan={'schemaVersion':'SpugAdmittedMainRoutes/v1','expected':{n:sha(before[n]) for n in ('smallapp-simple-settings.json','smallapp-entry-settings.json','smallapp-bridge.private.json')},
  'runtimeAdapterSha256':before['runtimeAdapterSha256'],'settings':{'smallapp-simple-settings.json':simple,'smallapp-entry-settings.json':entry},'bridge':bridge,'files':files,'receipts':receipts,'productionEnabled':False,'restorePerformed':False}
 p=PRIVATE/'spug-route-plan.private.json'
 if p.exists():assert json.loads(p.read_text(encoding='utf-8'))==plan,'SPUG_PLAN_CHANGED'
 else:p.write_bytes(canonical(plan))
 print(json.dumps({'state':'PLAN_READY','admittedTargets':['172.30.30.58','172.30.30.59'],'productionEnabled':False,'restorePerformed':False}))
def apply():
 plan=json.loads((PRIVATE/'spug-route-plan.private.json').read_text(encoding='utf-8'))
 adapter=RUNTIME/'ops/spug/smallapp_adapter.py';raw=adapter.read_bytes()
 assert hashlib.sha256(raw).hexdigest()==plan['runtimeAdapterSha256'],'RUNTIME_ADAPTER_CHANGED'
 bridgepath=RUNTIME/'private/smallapp-bridge.private.json'
 assert sha(json.loads(bridgepath.read_text(encoding='utf-8')))==plan['expected'][bridgepath.name],'SPUG_BRIDGE_CHANGED'
 code="""import hashlib,json,pathlib,sys
v=json.load(sys.stdin);root=pathlib.Path('/var/lib/intruoyi-spug')
def sha(d):return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
for n in v['settings']:assert sha(json.loads((root/n).read_text()))==v['expected'][n], 'SPUG_SETTINGS_CHANGED'
print(json.dumps({'checked':True}))
"""
 docker(code,plan)
 newline='\r\n' if b'\r\n' in raw else '\n';text=raw.decode('utf-8')
 needle="        self.target_refs = config.get('targetConfigRefs')"
 insert=newline.join([needle,"        self.selected_target_preflight = config.get('selectedTargetPreflight', False)","        if type(self.selected_target_preflight) is not bool:","            raise Refused('W01_TARGET_PREFLIGHT_CAPABILITY_INVALID')"])
 assert text.count(needle)==1 and 'self.selected_target_preflight' not in text,'RUNTIME_PATCH_CONTEXT_CHANGED'
 text=text.replace(needle,insert)
 needle='        payload = self.call(self.selection_url)'
 assert text.count(needle)==1,'RUNTIME_SELECTION_CONTEXT_CHANGED'
 text=text.replace(needle,newline.join(['        endpoint = self.selection_url','        if self.selected_target is not None and self.selected_target_preflight:',"            endpoint += '?targetConfigRef=' + urllib.parse.quote(self.selected_target, safe='')",'        payload = self.call(endpoint)']))
 ast.parse(text)
 (PRIVATE/'runtime-adapter.before.py').write_bytes(raw)
 for name,value in plan['files'].items():
  p=RUNTIME/'private'/name;data=canonical(value)
  if p.exists():assert p.read_bytes()==data,'SPUG_NEW_FILE_CONFLICT'
  else:
   with p.open('xb') as f:f.write(data)
  assert p.read_bytes()==data
 adapter.write_bytes(text.encode('utf-8'));ast.parse(adapter.read_bytes())
 bridgepath.write_bytes(canonical(plan['bridge']))
 install="""import hashlib,json,os,pathlib,signal,sys
v=json.load(sys.stdin);root=pathlib.Path('/var/lib/intruoyi-spug')
def raw(d):return json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
for n in v['settings']:assert hashlib.sha256(raw(json.loads((root/n).read_bytes()))).hexdigest()==v['expected'][n], 'SPUG_SETTINGS_CHANGED'
for n,d in v['settings'].items():
 p=root/n;backup=root/(n+'.restore-targets-20261104.before')
 if not backup.exists():backup.write_bytes(p.read_bytes());backup.chmod(0o600)
 staged=root/(n+'.restore-targets-20261104.tmp');staged.write_bytes(raw(d));staged.chmod(0o600);os.replace(staged,p)
 assert json.loads(p.read_bytes())==d
matches=[]
for p in pathlib.Path('/proc').glob('[0-9]*/cmdline'):
 try:args=p.read_bytes().split(b'\\0')
 except FileNotFoundError:continue
 if args[:3]==[b'python3',b'-B',b'/opt/intruoyi-spug/smallapp_entry.py']:matches.append(int(p.parent.name))
assert len(matches)==1,'OWN_ENTRY_PROCESS_AMBIGUOUS'
os.kill(matches[0],signal.SIGTERM)
print(json.dumps({'settingsInstalled':True,'entryPidReloaded':matches[0],'sharedServiceRestarted':False,'restorePerformed':False}))
"""
 result=docker(install,plan)
 (PRIVATE/'spug-route-installation.json').write_bytes(canonical(result))
 print(json.dumps(result))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','apply']);args=p.parse_args()
 prepare() if args.action=='prepare' else apply()
