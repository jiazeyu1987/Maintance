"""Verify the already-issued clearance read-only; never repeat authorization."""
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
need(installed['sourceCommit']==INSTALL['sourceCommit'] and installed['targetConfigRef']==TARGET,'INSTALLATION_CHANGED')
owner=read(installed['ownerConfigurationPin']);control=read(installed['controlConfigurationPin'])
custody=read(INSTALL['failureCustodyPin'])
need(custody['fullShaRead'] and custody['operationId']==OPERATION and len(custody['originalPins'])==2842,'FAILURE_CUSTODY_INVALID')
def original():
 for ref in custody['originalPins']:
  p=pathlib.Path(ref['path']);s=p.lstat()
  need(p.resolve()==p and stat.S_ISREG(s.st_mode) and identity(s)==custody['identities'][str(p)],'FAILURE_IDENTITY_CHANGED')
  if ref['bytes']<1024*1024:need(pin(p)==ref,'FAILURE_CONTENT_CHANGED')
original()
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from recovery_retained_retry import validate_clearance,observe
from recovery_main_target import published_endpoint
operation=root/'recovery-operations'/OPERATION
configuration=json.loads((operation/'configuration.json').read_bytes());request=json.loads((operation/'request.json').read_bytes())
need(request['targetConfigRef']==TARGET and request['recoveryPointRef']==POINT,'ORIGINAL_REQUEST_CHANGED')
need(configuration['targets']==owner['targets'],'TARGET_CONFIGURATION_CHANGED')
target=owner['targets'][TARGET];claim=pathlib.Path(target['replacement']['stateRoot'])/OPERATION
clearance=validate_clearance(target,claim)
need(clearance is not None and not (claim/'recovery-consumption.json').exists(),'CLEARANCE_NOT_AVAILABLE')
ready=json.loads((claim/'recovery-ready.json').read_bytes())
need(read(ready['clearancePin'])==clearance,'READY_CLEARANCE_CHANGED')
release=read(ready['releasePin']);need(release['clearancePin']==ready['clearancePin'],'RELEASE_CHANGED')
need(all(clearance[k]==request[k] for k in ('operationId','sourceConfigRef','targetConfigRef','recoveryPointRef')),'CLEARANCE_SCOPE_CHANGED')
proof=read(clearance['mainProtectionRecoveryPin'])
expected=[]
if target['mainApplication'].get('archiveMountProtection') is not None:expected.append('archive')
if published_endpoint(target,'minio') is not None:expected.append('published')
need(sorted(v['kind'] for v in proof['releasePins'])==sorted(expected),'CONFIGURED_PROTECTION_RELEASE_INVALID')
need(not pathlib.Path('/var/lib/spug-restore-resources/active.json').exists(),'RESERVATION_NOT_RELEASED')
observation=observe(configuration,request,operation,885)
original()
print(json.dumps(dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 operationId=OPERATION,sourceConfigRef=request['sourceConfigRef'],recoveryPointRef=POINT,targetConfigRef=TARGET,
 originalState='FAILED_RETAINED',originalFailureFilesUnchanged=len(custody['originalPins']),
 originalFullShaCustodyPin=INSTALL['failureCustodyPin'],originalProtectionsPreciselyReleased=True,
 configuredProtectionKinds=expected,clearancePin=ready['clearancePin'],resourceReleasePin=ready['releasePin'],
 mainProtectionRecoveryPin=clearance['mainProtectionRecoveryPin'],newRequestSamePointAndTarget=True,
 tableCount=observation['tableCount'],writersRemainStopped=True,restoreDispatched=False,
 verificationOnly=True,serverWrites=False)))
'''

if __name__ == '__main__':
    output=TASK/'allocator-retained-recovery-clearance-58.json';assert not output.exists()
    install=allocator_installation('58')
    assert install['failedOriginalFilesPreserved']==2842
    values=dict(ROOT='/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3',INSTALL=install,
        TARGET='intruoyi-main-58-safe-restore-20261104-v1',POINT='smallapp-ae9f83a19bb84ec28f27b5ca666bf62c',
        OPERATION='smallapp-c21bb7ce9f5b4668b850c37a80964786')
    report=remote('172.30.30.58','\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+SCRIPT,240)
    write(output,report);print(json.dumps(report))
