"""Append same-point clearance through the existing retained recovery contract."""
import json
from common import TASK, remote, write, allocator_installation

SCRIPT = r'''
import datetime,hashlib,json,pathlib,stat,sys
root=pathlib.Path(ROOT)
def need(value,code):
 if not value:raise ValueError(code)
def pin(p):
 p=pathlib.Path(p);raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(ref):need(pin(ref['path'])==ref,'PIN_CHANGED');return json.loads(pathlib.Path(ref['path']).read_bytes())
def identity(s):return [s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns]
installed=read(INSTALL['currentReceiptPin'])
need(installed['sourceCommit']==COMMIT and installed['targetConfigRef']==TARGET,'INSTALLATION_CHANGED')
owner=read(installed['ownerConfigurationPin']);control=read(installed['controlConfigurationPin'])
custody=read(INSTALL['failureCustodyPin'])
need(custody['fullShaRead'] and custody['operationId']==OPERATION and len(custody['originalPins'])==2842,'FAILURE_CUSTODY_INVALID')
def original():
 for ref in custody['originalPins']:
  p=pathlib.Path(ref['path']);s=p.lstat()
  need(p.resolve()==p and stat.S_ISREG(s.st_mode) and identity(s)==custody['identities'][str(p)],'FAILURE_IDENTITY_CHANGED')
  if ref['bytes']<1024*1024:need(pin(p)==ref,'FAILURE_CONTENT_CHANGED')
original()
need(pin('/var/lib/spug-restore-resources/active.json')==POINTER,'RETAINED_POINTER_CHANGED')
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from recovery_retained_retry import authorize,validate_clearance,observe
operation=root/'recovery-operations'/OPERATION
configuration=json.loads((operation/'configuration.json').read_bytes());request=json.loads((operation/'request.json').read_bytes())
need(request['targetConfigRef']==TARGET and request['recoveryPointRef']==POINT,'ORIGINAL_REQUEST_CHANGED')
need(configuration['targets']==owner['targets'],'TARGET_CONFIGURATION_CHANGED')
result=authorize(configuration,request,operation,
 'User requested this new production incremental backup to be restored to both original MAIN targets. Continue the same History367 point on MAIN58 with a new genuine Spug operation after correcting the frozen allocator defect; preserve History368 FAILED_RETAINED and all originals, transfer only its exact protections, and keep unverified application writers stopped.',885)
claim=pathlib.Path(configuration['targets'][TARGET]['replacement']['stateRoot'])/OPERATION
clearance=validate_clearance(configuration['targets'][TARGET],claim)
proof=read(clearance['mainProtectionRecoveryPin'])
need({v['kind'] for v in proof['releasePins']}=={'archive','published'},'MAIN_PROTECTION_RELEASE_INVALID')
need(not pathlib.Path('/var/lib/spug-restore-resources/active.json').exists(),'RESERVATION_NOT_RELEASED')
observation=observe(configuration,request,operation,885)
original()
out=dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 operationId=OPERATION,sourceConfigRef=request['sourceConfigRef'],recoveryPointRef=POINT,targetConfigRef=TARGET,
 originalState='FAILED_RETAINED',originalFailureFilesUnchanged=len(custody['originalPins']),
 originalFullShaCustodyPin=INSTALL['failureCustodyPin'],originalProtectionsPreciselyReleased=True,
 clearancePin=result['clearancePin'],resourceReleasePin=result['releasePin'],
 mainProtectionRecoveryPin=clearance['mainProtectionRecoveryPin'],newRequestSamePointAndTarget=True,
 tableCount=observation['tableCount'],writersRemainStopped=True,restoreDispatched=False)
print(json.dumps(out))
'''

if __name__ == '__main__':
    output=TASK/'allocator-retained-recovery-clearance-58.json';assert not output.exists()
    install=allocator_installation('58')
    preflight=json.loads((TASK/'allocator-upgrade-preflight-58.json').read_text(encoding='utf8'))
    assert install['status']=='PASS' and install['failedOriginalFilesPreserved']==2842
    values=dict(ROOT='/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3',INSTALL=install,
        COMMIT=install['sourceCommit'],TARGET='intruoyi-main-58-safe-restore-20261104-v1',
        POINT='smallapp-ae9f83a19bb84ec28f27b5ca666bf62c',OPERATION='smallapp-c21bb7ce9f5b4668b850c37a80964786',
        POINTER=preflight['activePointerPin'])
    report=remote('172.30.30.58','\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+SCRIPT,240)
    write(output,report);print(json.dumps(report))
