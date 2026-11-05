"""Use installed read-only catalogue routines against the exact new FULL."""
import json
from repair_preflight import remote,TASK
SCRIPT=r'''
import datetime,json,pathlib,sys
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3')
receipt=json.loads((root/'target-installation.json').read_bytes())
control=json.loads(pathlib.Path(receipt['controlConfigurationPin']['path']).read_bytes())
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from recovery_control_smallapp_native import Native
from recovery_control_restore_catalogue import bind_archive_chain,source_admits
receipt=json.loads((root/'target-installation.json').read_bytes())
native=Native(receipt['controlConfigurationPin'])
owner=native.document(receipt['ownerConfigurationPin'])
source=owner['sources']['intruoyi-57-safe-20261024-v1']
request={'sourceConfigRef':'intruoyi-57-safe-20261024-v1','recoveryPointRef':'smallapp-73cd541a95d84d6a86f9d693e4053c75'}
admitted=source_admits(native,source,request)
resolved,binding=bind_archive_chain(source,request)
assert binding['pointPin']['sha256']=='af95ffa94e9478bd32935c6e0c662aa5590854a0cda7597b84a25abd81a8f128'
assert len(resolved['repositoryPointPins'])==1
print(json.dumps({'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS','sourceLiveEligible':request['recoveryPointRef'] in admitted,'request':request,'targetConfigRef':receipt['targetConfigRef'],'pointPin':binding['pointPin'],'evidencePinsChecked':len(binding['evidencePins']),'orderedChainLength':len(resolved['repositoryPointPins']),'readOnly':True}))
'''
if __name__=='__main__':
 r=remote('172.30.30.58',SCRIPT,90)
 (TASK/'target-archive-admission.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(r))
