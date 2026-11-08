"""Authorize one new same-point request from the proven no-mutation 370 failure."""
import json
from common import TASK,remote,write
SCRIPT=r'''
import datetime,hashlib,json,pathlib,stat,sys
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3')
def need(value,code):
 if not value:raise ValueError(code)
def pin(p):
 p=pathlib.Path(p);raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(ref):need(pin(ref['path'])==ref,'PIN_CHANGED');return json.loads(pathlib.Path(ref['path']).read_bytes())
receipt=read(INSTALL['currentReceiptPin']);owner=read(receipt['ownerConfigurationPin']);control=read(receipt['controlConfigurationPin'])
need(receipt['sourceCommit']==INSTALL['sourceCommit'] and owner['targets'].keys()=={TARGET},'INSTALLATION_CHANGED')
custody=read(INSTALL['failureCustodyPin']);need(custody['fullShaRead'] and custody['operationId']==OPERATION and len(custody['originalPins'])==2916,'FAILURE_CUSTODY_INVALID')
def originals():
 for ref in custody['originalPins']:
  p=pathlib.Path(ref['path']);s=p.lstat()
  need(p.resolve()==p and stat.S_ISREG(s.st_mode) and [s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns]==custody['identities'][str(p)],'FAILURE_IDENTITY_CHANGED')
  if ref['bytes']<1024*1024:need(pin(p)==ref,'FAILURE_CONTENT_CHANGED')
originals();need(not pathlib.Path('/var/lib/spug-restore-resources/active.json').exists(),'ACTIVE_RESERVATION')
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from recovery_retained_retry import authorize,validate_clearance,observe,compare_quiescence
op=root/'recovery-operations'/OPERATION;configuration=json.loads((op/'configuration.json').read_bytes());request=json.loads((op/'request.json').read_bytes())
need(configuration['targets']==owner['targets'] and request['recoveryPointRef']==POINT and request['targetConfigRef']==TARGET,'ORIGINAL_BINDING_CHANGED')
result=authorize(configuration,request,op,
 'User authorized the new History367 production incremental point to both original MAIN targets. Continue after the proven pre-mutation History370 frontend health failure. Preserve History368, History369 and History370 originals, the exact consumed clearance and inherited quiesced service state; do not start unverified writers. A new restore must be a single genuine Spug request for the same point and target.',885,no_mutation=True)
claim=root/'replacement-state'/OPERATION;clearance=validate_clearance(owner['targets'][TARGET],claim)
need(clearance['schemaVersion']=='RetainedReplacementRecovery/v2' and clearance['failurePhase']=='BEFORE_MUTATION' and clearance['inheritedQuiescencePin']==EXPECTED_INHERITED,'CLEARANCE_SCOPE_CHANGED')
need(not (claim/'recovery-consumption.json').exists(),'CLEARANCE_ALREADY_CONSUMED')
observation=observe(configuration,request,op,885,False);compare_quiescence(observation,read(clearance['observationPin']))
originals()
out=dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),operationId=OPERATION,
 sourceConfigRef=request['sourceConfigRef'],recoveryPointRef=POINT,targetConfigRef=TARGET,
 originalState='FAILED_RETAINED',originalFailureFilesUnchanged=2916,originalFullShaCustodyPin=INSTALL['failureCustodyPin'],
 clearancePin=result['clearancePin'],resourceReleasePin=result['releasePin'],inheritedQuiescencePin=clearance['inheritedQuiescencePin'],
 noMutationReleasePin=clearance['noMutationReleasePin'],writersRemainStopped=True,tableCount=885,
 newRequestSamePointAndTarget=True,restoreDispatched=False)
print(json.dumps(out))
'''
if __name__=='__main__':
 output=TASK/'packaged-frontend-retained-recovery-clearance-58.json';assert not output.exists()
 install=json.loads((TASK/'packaged-frontend-target-installation-58.json').read_text(encoding='utf8'));assert install['status']=='PASS' and install['failedOriginalFilesPreserved']==2916
 candidate=json.loads((TASK/'frontend-retained-recovery-clearance-58.json').read_text(encoding='utf8'));assert candidate['status']=='PASS'
 values=dict(INSTALL=install,TARGET='intruoyi-main-58-safe-restore-20261104-v1',OPERATION='smallapp-e61ca1c4b93f4aa3ab5a70eca399c36d',
  POINT='smallapp-ae9f83a19bb84ec28f27b5ca666bf62c',EXPECTED_INHERITED=candidate['clearancePin'])
 result=remote('172.30.30.58','\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+SCRIPT,240)
 write(output,result);print(json.dumps(result))
