"""Record the exact submitted build identity; never alter executor history."""
from pathlib import Path
import json,sqlite3,sys
path=Path(__file__).with_name('selected-release.json');selection=json.loads(path.read_text('utf-8'))
with sqlite3.connect('file:C:/SpugHandoff/release/state/state.sqlite3?mode=ro',uri=True) as db:state=json.loads(db.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
job=next(j for j in state['jobs'] if j['id']==sys.argv[1])
assert job['action'] in ('backend-patch-build','build-release')
assert job['payload']['commit']==selection['commit']
key='backendPatchTag' if job['action']=='backend-patch-build' else 'fullReleaseTag'
assert job.get('releaseTag') and (key not in selection or selection[key]==job['releaseTag'])
selection[key]=job['releaseTag']
if key=='backendPatchTag':selection['baselineId']=job['payload']['baselineId']
selection[key+'BuildJobId']=job['id']
path.write_text(json.dumps(selection,indent=2)+'\n',encoding='utf-8')
assert json.loads(path.read_text('utf-8'))==selection
print(json.dumps(selection))
