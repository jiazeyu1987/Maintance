"""Rehash every original failed file and audit its one exact new consumer."""
import json
from common import TASK, PRIVATE, now, remote, write, restore_kind, allocator_installation, restore_clearance

SCRIPT = r'''
import datetime,hashlib,json,os,pathlib,stat,time,sys
root=pathlib.Path(ROOT);deadline=time.monotonic()+890
def identity(s):return (s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
for ref in PINS:
 p=pathlib.Path(ref['path']);before=p.lstat()
 assert p.resolve()==p and stat.S_ISREG(before.st_mode) and before.st_nlink==1,'ORIGINAL_PATH_CHANGED'
 sha=hashlib.sha256();size=0
 with os.fdopen(os.open(p,os.O_RDONLY|os.O_NOFOLLOW),'rb') as stream:
  assert identity(os.fstat(stream.fileno()))==identity(before)
  while True:
   assert time.monotonic()<deadline,'ORIGINAL_REHASH_DEADLINE'
   raw=stream.read(1024*1024)
   if not raw:break
   sha.update(raw);size+=len(raw)
  assert identity(os.fstat(stream.fileno()))==identity(before)
 assert identity(p.lstat())==identity(before) and size==ref['bytes'] and sha.hexdigest()==ref['sha256'],'ORIGINAL_FAILURE_CHANGED'
def read(ref):
 raw=pathlib.Path(ref['path']).read_bytes();assert len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256'];return json.loads(raw)
control=read(INSTALL['controlConfigurationPin']);owner=read(INSTALL['ownerConfigurationPin'])
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from recovery_retained_retry import validate_clearance
target=owner['targets'][TARGET]
for operation,receipt,successor,expected_mutation in (
 (ORIGINAL,CLEARANCE,SECOND,True),(SECOND,SECOND_CLEARANCE,THIRD,False),
 (THIRD,THIRD_CLEARANCE,SUCCESS,False)):
 claim=pathlib.Path(target['replacement']['stateRoot'])/operation
 clearance=validate_clearance(target,claim);assert clearance==read(receipt['clearancePin'])
 assert all(clearance[k]==SUCCESS_REQUEST[k] for k in ('targetConfigRef','sourceConfigRef','recoveryPointRef'))
 consumer=json.loads((claim/'recovery-consumption.json').read_bytes())
 assert consumer['replacementOperationId']==successor and consumer['clearancePin']==receipt['clearancePin']
 result=json.loads((root/'recovery-operations'/operation/'worker-result.json').read_bytes())
 assert result['state']=='FAILED_RETAINED' and result['actualExitCode']==1
 assert result['data']['mutationDispatched'] is expected_mutation
assert read(SECOND_CLEARANCE['clearancePin'])['inheritedQuiescencePin']==CLEARANCE['clearancePin']
assert read(THIRD_CLEARANCE['clearancePin'])['inheritedQuiescencePin']==SECOND_CLEARANCE['clearancePin']
assert json.loads((root/'recovery-operations'/SUCCESS/'worker-result.json').read_bytes())['state']=='SUCCEEDED'
print(json.dumps(dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 originalOperationId=ORIGINAL,secondFailedOperationId=SECOND,thirdFailedOperationId=THIRD,newOperationId=SUCCESS,protectedFiles=len(PINS),protectedBytes=sum(p['bytes'] for p in PINS),
 exactFailureConsumerChain=[ORIGINAL,SECOND,THIRD,SUCCESS],allThreeOriginalFailuresUnchanged=True,
 allOriginalBytesRead=True,originalFailureUnchanged=True,exactSamePointClearanceConsumedOnce=True,serverWrites=False)))
'''

if __name__=='__main__':
    output=TASK/'failed-368-closeout-preservation.json';assert not output.exists()
    for suffix in ('58','59'):
        value=json.loads((TASK/('restore-'+suffix+'-native-evidence.json')).read_text(encoding='utf8'))
        assert value['status']=='PASS' and value['actualExitCode']==0
    success=json.loads((TASK/(restore_kind('58')+'-ui-submission.json')).read_text(encoding='utf8'))['request']
    values=dict(ROOT='/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3',
        PINS=sum([json.loads((PRIVATE/('failed-'+number+'-all-pins.private.json')).read_text(encoding='utf8'))['pins'] for number in ('368','369','370')],[]),
        INSTALL=allocator_installation('58'),TARGET=success['targetConfigRef'],SUCCESS=success['operationId'],
        ORIGINAL='smallapp-c21bb7ce9f5b4668b850c37a80964786',
        SECOND='smallapp-b4f35606e4854516960050a76473038b',
        THIRD='smallapp-e61ca1c4b93f4aa3ab5a70eca399c36d',THIRD_CLEARANCE=restore_clearance('58'),SUCCESS_REQUEST=success,
        SECOND_CLEARANCE=json.loads((TASK/'frontend-retained-recovery-clearance-58.json').read_text(encoding='utf8')),
        CLEARANCE=json.loads((TASK/'allocator-retained-recovery-clearance-58.json').read_text(encoding='utf8')))
    result=remote('172.30.30.58','\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+SCRIPT,910)
    write(output,result);print(json.dumps(result))
