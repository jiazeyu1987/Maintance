"""Select an explicit new attempt without altering any historic request."""
import json
from common import TASK,write
installed=json.loads((TASK/'packaged-frontend-target-installation-58.json').read_text(encoding='utf-8'))
clearance=json.loads((TASK/'packaged-frontend-retained-recovery-clearance-58.json').read_text(encoding='utf-8'))
assert installed['status']==clearance['status']=='PASS' and installed['actualPackagedConstructorVerified']
for name in ('allocator-selected-installations','restore-selected-attempts','restore-selected-clearances','restore-selected-source-baselines'):
 p=TASK/(name+'.json');saved=TASK/(name+'-before-packaged-frontend.json');assert not saved.exists()
 value=json.loads(p.read_text(encoding='utf-8'))
 saved.write_bytes(p.read_bytes())
 if name=='allocator-selected-installations':
  assert value['targets']['58']=='frontend-target-installation-58.json'
  value['targets']['58']='packaged-frontend-target-installation-58.json'
  value['contracts']['58']='target-packaged-frontend-contract-58.json'
 elif name=='restore-selected-attempts':
  assert value['targets']['58']['kind']=='restore-58-r3'
  value['targets']['58']=dict(kind='restore-58-r4',predecessorKind='restore-58-r3',
   predecessorOperationId='smallapp-e61ca1c4b93f4aa3ab5a70eca399c36d',predecessorState='FAILED_RETAINED',
   reason='Actual packaged constructor binds the exact owner frontend profile; retain all three failures and consume the formal same-point clearance once')
 elif name=='restore-selected-clearances':
  assert value['targets']['58']=='frontend-retained-recovery-clearance-58.json'
  value['targets']['58']='packaged-frontend-retained-recovery-clearance-58.json'
 else:value['targets']['58']='before-restore-58-r4-57.json'
 write(p,value)
print(json.dumps(dict(status='SELECTED',kind='restore-58-r4',restoreDispatched=False)))
