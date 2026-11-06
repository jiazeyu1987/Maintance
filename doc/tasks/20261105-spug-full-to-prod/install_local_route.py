"""Add the independently admitted .57 route, preserving current .58/.59 settings."""
import argparse,copy,hashlib,json,subprocess,urllib.request
from pathlib import Path
from install_prod_control import APP,TARGET,PRIVATE,TASK,ROOT,PYTHON

RUNTIME=Path('C:/Spug/runtime')
CONTAINER='intruoyi-spug-transfer-spug-1'
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def sha(value):return hashlib.sha256(canonical(value)).hexdigest()
def docker(code,value=None):
    r=subprocess.run(['C:/Users/D01021/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe','exec','-i',CONTAINER,'python3','-B','-c',code],input=None if value is None else canonical(value),capture_output=True)
    if r.returncode:
        (PRIVATE/'local-route-error.private.log').write_bytes(r.stdout+r.stderr);raise ValueError('LOCAL_ROUTE_FAILED_SEE_PRIVATE_LOG')
    return json.loads(r.stdout)

READ="""import pathlib,json;root=pathlib.Path('/var/lib/intruoyi-spug');print(json.dumps({n:json.loads((root/n).read_bytes()) for n in ['smallapp-simple-settings.json','smallapp-entry-settings.json']}))"""

def prepare():
    receipt=json.loads((TASK/'control-configure-installation.json').read_text(encoding='utf-8'))
    assert receipt['targetConfigRef']==TARGET and receipt['state']=='INSTALLED_PENDING_LOCAL_ROUTE'
    headers=json.loads((PRIVATE/'target-control-headers.private.json').read_text(encoding='utf-8'))
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(urllib.request.Request('http://127.0.0.1:43657/selections?targetConfigRef='+TARGET,headers=headers['headers']),timeout=100) as r:
        admitted=json.load(r);assert r.status==200
    rows=[a for a in admitted['applications'] if a['applicationId']==APP]
    assert len(rows)==1 and TARGET in rows[0]['freshTargetConfigRefs'],'ACTUAL_TARGET_ADMISSION_REQUIRED'
    before=docker(READ);bridgepath=RUNTIME/'private/smallapp-bridge.private.json'
    before[bridgepath.name]=json.loads(bridgepath.read_text(encoding='utf-8'))
    (PRIVATE/'route-before.private.json').write_bytes(canonical(before))
    settings=copy.deepcopy({n:v for n,v in before.items() if n!=bridgepath.name});bridge=copy.deepcopy(before[bridgepath.name])
    binding=next(a for a in settings['smallapp-simple-settings.json']['bindings'] if a['applicationId']==APP)
    assert '172.30.30.57' not in binding['overwriteTargetServers'],'PRODUCTION_ROUTE_EXISTS'
    binding['overwriteTargetServers']['172.30.30.57']=TARGET
    template=copy.deepcopy(next(r for r in binding['restoreProgressBindings'].values() if r['server']=='172.30.30.57'))
    template.update(progressRoot=ROOT,pythonPath=PYTHON)
    assert template['sshTransport']==dict(host='host.docker.internal',port=18557)
    binding['restoreProgressBindings'][TARGET]=template
    app=next(a for a in settings['smallapp-entry-settings.json']['applications'] if a['applicationId']==APP)
    assert TARGET not in app['targetConfigRefs'];app['targetConfigRefs'].append(TARGET)
    registration=dict(schemaVersion='ApplicationRegistration/v1',applicationId=APP,sourceConfigRef=APP,displayName='IntRuoyi 正式服备份',allowedRestoreTargets=[dict(configRef=binding['overwriteTargetServers'][h]) for h in sorted(binding['overwriteTargetServers'])])
    app['registrationSha256']=sha(registration)
    config=json.loads((RUNTIME/'private'/bridge['sourceConnections'][APP]).read_text(encoding='utf-8'))
    origin='http://host.docker.internal:43657';credential='main-restore-57-headers-20261105-v2.private.json';filename='main-restore-57-bridge-20261105-v2.private.json'
    config.update(submitUrl=origin+'/operations',queryUrlTemplate=origin+'/operations/{operationId}',selectionUrl=origin+'/selections',sourceConfigRefs=[APP],targetConfigRefs=[TARGET],selectedTargetPreflight=True,credentialRef=credential,registrationBindings=[])
    assert TARGET not in bridge['targetConnections'];bridge['targetConnections'][TARGET]=filename
    adapter=RUNTIME/'ops/spug/smallapp_adapter.py'
    assert b'self.selected_target_preflight' in adapter.read_bytes(),'CURRENT_ADAPTER_CAPABILITY_REQUIRED'
    plan=dict(expected={n:sha(v) for n,v in before.items()},settings=settings,bridge=bridge,files={filename:config,credential:headers},adapterSha256=hashlib.sha256(adapter.read_bytes()).hexdigest())
    (PRIVATE/'production-route-plan.private.json').write_bytes(canonical(plan))
    report=dict(status='PLAN_READY',targetConfigRef=TARGET,liveAdmission=True,otherRoutesPreserved=True,restorePerformed=False)
    (TASK/'local-route-preflight.json').write_bytes(canonical(report));print(json.dumps(report))

INSTALL=r'''
import hashlib,json,os,pathlib,signal,sys
v=json.load(sys.stdin);root=pathlib.Path('/var/lib/intruoyi-spug')
def raw(d):return json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
for n in v['settings']:assert hashlib.sha256(raw(json.loads((root/n).read_bytes()))).hexdigest()==v['expected'][n],'SPUG_SETTINGS_CHANGED'
matches=[]
for p in pathlib.Path('/proc').glob('[0-9]*/cmdline'):
 try:args=p.read_bytes().split(b'\0')
 except FileNotFoundError:continue
 if args[:3]==[b'python3',b'-B',b'/opt/intruoyi-spug/smallapp_entry.py']:matches.append(int(p.parent.name))
assert len(matches)==1,'OWN_ENTRY_PROCESS_AMBIGUOUS'
for n,d in v['settings'].items():
 p=root/n;backup=root/(n+'.production-main-20261105.before');assert not backup.exists(),'INSTALL_BACKUP_EXISTS'
 backup.write_bytes(p.read_bytes());backup.chmod(0o600)
 staged=root/(n+'.production-main-20261105.tmp');staged.write_bytes(raw(d));staged.chmod(0o600);os.replace(staged,p)
 assert json.loads(p.read_bytes())==d
os.kill(matches[0],signal.SIGTERM)
print(json.dumps(dict(status='PASS',entryPidReloaded=matches[0],sharedServiceRestarted=False,restorePerformed=False)))
'''
def apply():
    plan=json.loads((PRIVATE/'production-route-plan.private.json').read_bytes())
    bridgepath=RUNTIME/'private/smallapp-bridge.private.json'
    assert sha(json.loads(bridgepath.read_bytes()))==plan['expected'][bridgepath.name]
    assert hashlib.sha256((RUNTIME/'ops/spug/smallapp_adapter.py').read_bytes()).hexdigest()==plan['adapterSha256']
    current=docker(READ)
    assert all(sha(current[n])==plan['expected'][n] for n in current),'SPUG_SETTINGS_CHANGED'
    for n,value in plan['files'].items():
        p=RUNTIME/'private'/n;assert not p.exists(),'NEW_ROUTE_FILE_EXISTS'
        with p.open('xb') as f:f.write(canonical(value))
        assert p.read_bytes()==canonical(value)
    backup=PRIVATE/'local-bridge.before-production.private.json';assert not backup.exists();backup.write_bytes(bridgepath.read_bytes())
    bridgepath.write_bytes(canonical(plan['bridge']));assert json.loads(bridgepath.read_bytes())==plan['bridge']
    report=docker(INSTALL,plan)
    (TASK/'local-route-installation.json').write_bytes(canonical(report));print(json.dumps(report))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','apply']);args=parser.parse_args()
    prepare() if args.action=='prepare' else apply()
