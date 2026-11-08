"""Refresh expired read-only observations while retaining their exact originals."""
import json,subprocess,sys
from common import TASK,write
assert not (TASK/'restore-58-r4-ui-submission.json').exists()
for phase in ('rollback-point','new-point'):
 p=TASK/('target-'+phase+'-admission-restore-58-r4.json')
 q=p.with_name(p.stem+'-before-entry3.json');assert not q.exists()
 original=p.read_bytes();assert json.loads(original)['status']=='PASS'
 q.write_bytes(original);assert q.read_bytes()==original;p.unlink()
for phase in ('rollback-point','new-point'):
 command=[sys.executable,'-X','utf8',str(TASK/'inspect_target_admission.py'),'58','--allocator']
 if phase=='new-point':command.append('--new-point')
 subprocess.run(command,check=True)
subprocess.run([sys.executable,'-X','utf8',str(TASK/'observe_baseline.py'),'57','--phase','before-restore-58-r4-entry3'],check=True)
path=TASK/'restore-selected-source-baselines.json';value=json.loads(path.read_text(encoding='utf8'))
assert value['targets']['58']=='before-restore-58-r4-57.json'
value['targets']['58']='before-restore-58-r4-entry3-57.json';write(path,value)
print(json.dumps(dict(status='REFRESHED',serverWrites=False,restoreDispatched=False)))
