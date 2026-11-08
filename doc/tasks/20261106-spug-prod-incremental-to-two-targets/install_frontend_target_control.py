"""Install the committed frontend health generation, preserving all old failures."""
import argparse,base64,hashlib,json
from common import TASK,PRIVATE,remote,write
from install_allocator_target_control import SCRIPT as BASE

def replace(text,old,new):
 assert text.count(old)==1,'INSTALL_CARRIER_ANCHOR_CHANGED'
 return text.replace(old,new)

SCRIPT=replace(BASE,"generation='allocator-'+COMMIT[:7]","generation='frontend-'+COMMIT[:7]")
left=SCRIPT.index('def reservation():');right=SCRIPT.index('\ndef workers():',left)
SCRIPT=SCRIPT[:left]+'''def reservation():
 need(not activepath.exists(),'ACTIVE_RESERVATION')
 if SUFFIX=='58':
  claim=pathlib.Path(target['replacement']['stateRoot'])/FAILED_OPERATION
  need(not (claim/'recovery-clearance.json').exists(),'UNEXPECTED_NEW_CLEARANCE')
  need(pin(root/'recovery-operations'/FAILED_OPERATION/'resource-no-mutation-release.json')==NO_MUTATION_RELEASE,'NO_MUTATION_RELEASE_CHANGED')
  prior=pathlib.Path(target['replacement']['stateRoot'])/'smallapp-c21bb7ce9f5b4668b850c37a80964786'
  need(json.loads((prior/'recovery-consumption.json').read_bytes())['replacementOperationId']==FAILED_OPERATION,'PREVIOUS_CONSUMER_CHANGED')
'''+SCRIPT[right:]
SCRIPT=replace(SCRIPT,"newowner['formalModuleDirectory']=str(engine/'formal')","newowner['formalModuleDirectory']=str(engine/'formal')\n if FRONTEND_PROFILE is not None:newowner['frontendReadiness']={TARGET:FRONTEND_PROFILE}")
start=SCRIPT.index(" code='import json,sys;");end=SCRIPT.index(' archive_receipt=',start)
SCRIPT=SCRIPT[:start]+''' code="""import json,pathlib,subprocess,sys
from types import SimpleNamespace
from recovery_control_smallapp_native import Native
from recovery_minimal_runtime import modules_from
from recovery_main_health import preflight
from recovery_retained_retry import inherited_quiescence,compare_quiescence,observe,verify_no_mutation
from recovery_engine import pin,pinned_json
modules=modules_from(sys.argv[2]);assert callable(modules['formal_schema_evidence'].restore_frozen_auto_increment)
native=Native(json.loads(sys.argv[1]));native.configuration()
owner=json.loads(pathlib.Path(sys.argv[5]).read_bytes());target=owner['targets'][sys.argv[3]]
def docker(args):
 p=subprocess.run(['docker',*args],capture_output=True,timeout=20);assert p.returncode==0;return p.stdout
rows={s['role']:json.loads(docker(['inspect',s['id']]))[0] for s in target['services']}
view=SimpleNamespace(config=target,config_services={s['role']:s for s in target['services']},
 frontend_readiness=owner.get('frontendReadiness',{}).get(sys.argv[3]),docker=docker,
 inspect=lambda identity:next(r for r in rows.values() if r['Id']==identity))
preflight(view)
if sys.argv[6]=='59':
 document=native.selections(selected_target=sys.argv[3])
 assert sys.argv[3] in next(a for a in document['applications'] if a['sourceConfigRef']==sys.argv[4])['freshTargetConfigRefs']
else:
 op=pathlib.Path(owner['operationsRoot'])/'smallapp-b4f35606e4854516960050a76473038b'
 original=json.loads((op/'configuration.json').read_bytes());request=json.loads((op/'request.json').read_bytes())
 refs={k:pin(op/name) for k,name in [('resultPin','worker-result.json'),('exitPin','child-exit.json')]}
 verify_no_mutation(original,request,op,refs,pin(op/'resource-no-mutation-release.json'))
 ref,previous=inherited_quiescence(target,request)
 compare_quiescence(observe(original,request,op,885,False),pinned_json(previous['observationPin']))
print('VALID')
"""
 need(run([newcontrol['pythonPin']['path'],'-B','-c',code,canonical(controlpin).decode(),str(engine/'formal'),TARGET,APP,ownerpin['path'],SUFFIX],env=dict(os.environ,**newcontrol['environment']),timeout=120).strip()==b'VALID','NEW_CONFIGURATION_INVALID')
'''+SCRIPT[end:]
SCRIPT=replace(SCRIPT,"({None:'zz-','r2':'zzz-','r3':'zzzz-'}[REVISION]+generation+'.conf')","(('zzzzz-' if SUFFIX=='58' else 'zzz-')+generation+'.conf')")
SCRIPT=replace(SCRIPT,"retainedReservationUnchanged=SUFFIX=='58' and CLEARANCE is None,","retainedReservationUnchanged=False,noMutationReservationAbsent=True,")
SCRIPT=replace(SCRIPT,"actualSelectionVerifiedBeforeActivation=LEGACY_VERIFIED,","actualSelectionVerifiedBeforeActivation=SUFFIX=='59',actualHealthContractVerified=True,frontendReadiness=FRONTEND_PROFILE,")

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('suffix',choices=['58','59']);parser.add_argument('--commit',required=True);args=parser.parse_args();suffix=args.suffix
 stem='frontend-target-installation-'+suffix;assert not (TASK/(stem+'.json')).exists()
 build=json.loads((TASK/'release-build-verification.json').read_text(encoding='utf8'));assert build['status']=='PASS' and build['targetCommit']==args.commit
 committed=json.loads((TASK/'frontend-health-implementation-commit.json').read_text(encoding='utf8'));assert committed['status']=='PASS' and committed['implementationCommit']==args.commit
 regression=json.loads((TASK/'frontend-health-regression-5.json').read_text(encoding='utf8'));assert regression['expectedResultObserved'] and regression['inputFilesUnchanged'] and regression['containerRemoved']
 preflight=json.loads((TASK/('frontend-upgrade-preflight-'+suffix+'.json')).read_text(encoding='utf8'));assert preflight['status']=='PASS'
 candidate=json.loads((TASK/('frontend-readiness-candidate-'+suffix+'.json')).read_text(encoding='utf8'));assert candidate['status']=='PASS'
 assert candidate['sourceSha256']==hashlib.sha256((TASK.parents[2]/'ops/recovery/recovery_main_health.py').read_bytes()).hexdigest()
 pins=[];no_mutation=None
 if suffix=='58':
  for name in ('failed-368-all-pins.private.json','failed-369-all-pins.private.json'):pins.extend(json.loads((PRIVATE/name).read_text(encoding='utf8'))['pins'])
  no_mutation=next(p for p in pins if p['path'].endswith('smallapp-b4f35606e4854516960050a76473038b/resource-no-mutation-release.json'))
  assert len(pins)==2879 and len({p['path'] for p in pins})==2879
 raw=(PRIVATE/('package-'+args.commit[:7])/'backup-restore-standard.tgz').read_bytes();assert hashlib.sha256(raw).hexdigest()==build['packageSha256']
 values=dict(ROOT=('/mnt/intruoyi-data/' if suffix=='59' else '/var/lib/docker/intruoyi-data/')+'spug-main-restore-20261104-v3',SUFFIX=suffix,
  COMMIT=args.commit,TARGET='intruoyi-main-'+suffix+'-safe-restore-20261104-v1',APP='intruoyi-57-safe-20261024-v1',
  FAILED_OPERATION='smallapp-b4f35606e4854516960050a76473038b',POINT='smallapp-ae9f83a19bb84ec28f27b5ca666bf62c',
  PACKAGE=base64.b64encode(raw).decode(),PACKAGE_SHA=build['packageSha256'],MANIFEST_SHA=build['fileManifestSha256'],
  PREFLIGHT=preflight,FAILURE_PINS=pins,CLEARANCE=None,LEGACY_VERIFIED=False,FRONTEND_PROFILE=candidate['profile'],NO_MUTATION_RELEASE=no_mutation)
 compile(SCRIPT,'frontend-installation-carrier','exec')
 result=remote('172.30.30.'+suffix,'\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+SCRIPT,1000)
 write(TASK/(stem+'.json'),result);print(json.dumps(result))
