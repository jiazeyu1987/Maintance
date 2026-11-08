"""Prepare exact task carriers; this step performs no server actions."""
from pathlib import Path
import json
from common import TASK
from install_frontend_target_control import SCRIPT as OLD

def replace(text, old, new):
    assert text.count(old)==1, old
    return text.replace(old,new)

code='''import json,pathlib,sys
import recovery_minimal_runtime as runtime
from recovery_control_smallapp_native import Native
from recovery_main_health import endpoint,ROLES
from recovery_retained_retry import inherited_quiescence,compare_quiescence,observe,verify_no_mutation
from recovery_engine import pin,pinned_json,write
native=Native(json.loads(sys.argv[1]));native.configuration()
owner=json.loads(pathlib.Path(sys.argv[5]).read_bytes());target=owner['targets'][sys.argv[3]]
root=pathlib.Path(sys.argv[7]);root.mkdir(mode=0o700)
reference=pin(sys.argv[5]);request={'operationId':'installation-constructor-boundary',
 'action':'RESTORE','targetConfigRef':sys.argv[3]}
chain=[(reference,None,{'recoveryPoint':'INSTALLATION_CONSTRUCTOR_BOUNDARY_NOT_RESTORE',
 'objects':{'method':'PHYSICAL_FILES'},'payloadPins':[],'versionPins':[]},reference)]
class BeforeDatabaseIO(Exception):pass
class Boundary(runtime.MinimalData):
 def database_uuid(self):
  assert self.frontend_readiness==owner['frontendReadiness'][sys.argv[3]],'PACKAGED_FRONTEND_PROFILE_NOT_PROPAGATED'
  assert {role:endpoint(self,role) for role in ROLES}==json.loads(sys.argv[8]),'ACTUAL_ENDPOINT_CHANGED'
  assert self.mutation_dispatched is False
  records=[p for p in self.original_pins if pathlib.Path(p['path']).name.startswith('native-')]
  assert len(records)>=3 and all(pinned_json(p)['mutation'] is False and pinned_json(p)['actualExitCode']==0 for p in records)
  write(root/'constructor-verification.json',dict(schemaVersion='TaskPackagedConstructorBoundary/v1',
   ownerConfigurationPin=reference,targetConfigRef=sys.argv[3],constructorModulePath=runtime.__file__,
   exactProfileFromActualOwner=True,healthEndpoints=json.loads(sys.argv[8]),nativeInvocationPins=records,
   noDatabaseIO=True,restoreDispatched=False))
  raise BeforeDatabaseIO()
subject=Boundary.__new__(Boundary)
try:subject.__init__(owner,request,None,{},chain,target,root,[])
except BeforeDatabaseIO:pass
else:raise AssertionError('ACTUAL_DATABASE_BOUNDARY_NOT_REACHED')
assert subject.archive_guard.fd==-1 and not subject.archive_guard.path_fds
assert callable(subject.modules['formal_schema_evidence'].restore_frozen_auto_increment)
op=pathlib.Path(owner['operationsRoot'])/'smallapp-e61ca1c4b93f4aa3ab5a70eca399c36d'
original=json.loads((op/'configuration.json').read_bytes());request=json.loads((op/'request.json').read_bytes())
refs={k:pin(op/name) for k,name in [('resultPin','worker-result.json'),('exitPin','child-exit.json')]}
verify_no_mutation(original,request,op,refs,pin(op/'resource-no-mutation-release.json'))
ref,previous=inherited_quiescence(target,request)
compare_quiescence(observe(original,request,op,885,False),pinned_json(previous['observationPin']))
print('VALID')
'''
script=replace(OLD,"generation='frontend-'+COMMIT[:7]","generation='packaged-frontend-'+COMMIT[:7]")
script=replace(script,"'smallapp-c21bb7ce9f5b4668b850c37a80964786'","'smallapp-b4f35606e4854516960050a76473038b'")
script=replace(script,'  observe(original,request,oldroot,885)','  observe(original,request,oldroot,885,False)')
start=script.index(' code="""');end=script.index(' archive_receipt=',start)
script=script[:start]+" code="+repr(code)+"\n need(run([newcontrol['pythonPin']['path'],'-B','-c',code,canonical(controlpin).decode(),str(engine/'formal'),TARGET,APP,ownerpin['path'],SUFFIX,str(root/'configuration'/('constructor-gate-'+generation)),canonical(EXPECTED_ENDPOINTS).decode()],env=dict(os.environ,**newcontrol['environment']),timeout=120).strip()==b'VALID','NEW_CONFIGURATION_INVALID')\n"+script[end:]
script=replace(script,"(('zzzzz-' if SUFFIX=='58' else 'zzz-')+generation+'.conf')","('zzzzzz-'+generation+'.conf')")
script=replace(script,'actualHealthContractVerified=True,',"actualHealthContractVerified=True,actualPackagedConstructorVerified=True,constructorStopsBeforeDatabaseIO=True,constructorEvidencePin=pin(root/'configuration'/('constructor-gate-'+generation)/'constructor-verification.json'),")
compile(script,'packaged-frontend-installation','exec')
(TASK/'packaged_frontend_install_script.py').write_text('SCRIPT = '+repr(script)+'\n',encoding='utf-8')

installer='''"""Install only the exact verified constructor fix on target 58."""
import argparse,base64,hashlib,json
from common import TASK,PRIVATE,remote,write
from packaged_frontend_install_script import SCRIPT
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--commit',required=True);args=parser.parse_args()
 output=TASK/'packaged-frontend-target-installation-58.json';assert not output.exists()
 build=json.loads((TASK/'release-build-verification.json').read_text(encoding='utf8'))
 committed=json.loads((TASK/'packaged-frontend-implementation-commit.json').read_text(encoding='utf8'))
 assert build['status']==committed['status']=='PASS' and build['targetCommit']==committed['implementationCommit']==args.commit
 regression=json.loads((TASK/'frontend-health-regression-7.json').read_text(encoding='utf8'))
 assert regression['expectedResultObserved'] and regression['inputFilesUnchanged'] and regression['containerRemoved']
 preflight=json.loads((TASK/'packaged-frontend-upgrade-preflight-58.json').read_text(encoding='utf8'));assert preflight['status']=='PASS'
 candidate=json.loads((TASK/'frontend-readiness-candidate-58.json').read_text(encoding='utf8'));assert candidate['status']=='PASS'
 pins=[]
 for n in ('368','369','370'):pins.extend(json.loads((PRIVATE/('failed-'+n+'-all-pins.private.json')).read_text(encoding='utf8'))['pins'])
 assert len(pins)==len({p['path'] for p in pins})==2916
 failed='smallapp-e61ca1c4b93f4aa3ab5a70eca399c36d'
 no_mutation=next(p for p in pins if p['path'].endswith(failed+'/resource-no-mutation-release.json'))
 raw=(PRIVATE/('package-'+args.commit[:7])/'backup-restore-standard.tgz').read_bytes();assert hashlib.sha256(raw).hexdigest()==build['packageSha256']
 values=dict(ROOT='/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3',SUFFIX='58',COMMIT=args.commit,
  TARGET='intruoyi-main-58-safe-restore-20261104-v1',APP='intruoyi-57-safe-20261024-v1',FAILED_OPERATION=failed,
  POINT='smallapp-ae9f83a19bb84ec28f27b5ca666bf62c',PACKAGE=base64.b64encode(raw).decode(),PACKAGE_SHA=build['packageSha256'],
  MANIFEST_SHA=build['fileManifestSha256'],PREFLIGHT=preflight,FAILURE_PINS=pins,CLEARANCE=None,LEGACY_VERIFIED=False,
  FRONTEND_PROFILE=candidate['profile'],NO_MUTATION_RELEASE=no_mutation,EXPECTED_ENDPOINTS=candidate['endpoints'])
 result=remote('172.30.30.58','\\n'.join(k+'='+repr(v) for k,v in values.items())+'\\n'+SCRIPT,1000)
 write(output,result);print(json.dumps(result))
'''
compile(installer,'install-packaged-frontend','exec')
(TASK/'install_packaged_frontend_control.py').write_text(installer,encoding='utf-8')
authorization=(TASK/'authorize_failed369_recovery.py').read_text(encoding='utf-8')
authorization=authorization.replace('369','370').replace('2879','2916')
authorization=authorization.replace('frontend-target-installation-58.json','packaged-frontend-target-installation-58.json')
authorization=authorization.replace('frontend-retained-recovery-clearance-58.json','packaged-frontend-retained-recovery-clearance-58.json')
authorization=authorization.replace('smallapp-b4f35606e4854516960050a76473038b','smallapp-e61ca1c4b93f4aa3ab5a70eca399c36d')
authorization=replace(authorization,"candidate=json.loads((TASK/'inherited-quiescence-candidate-58.json').read_text(encoding='utf8'));assert candidate['status']=='PASS'",
 "candidate=json.loads((TASK/'frontend-retained-recovery-clearance-58.json').read_text(encoding='utf8'));assert candidate['status']=='PASS'")
authorization=replace(authorization,"EXPECTED_INHERITED=candidate['inheritedQuiescencePin']","EXPECTED_INHERITED=candidate['clearancePin']")
authorization=replace(authorization,'Preserve History368 and History370 originals','Preserve History368, History369 and History370 originals')
compile(authorization,'authorize370','exec')
(TASK/'authorize_failed370_recovery.py').write_text(authorization,encoding='utf-8')
print(json.dumps({'status':'PREPARED','serverActions':False}))
