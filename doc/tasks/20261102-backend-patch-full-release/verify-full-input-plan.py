"""Static full-release migration plan for the exact selected committed source."""
from pathlib import Path
from collections import Counter
import json,sqlite3,subprocess,sys
task=Path(__file__).parent
sys.path.insert(0,'C:/SpugHandoff/release/source/ops/spug/release-center')
from intruoyi_build import migration_inputs,historical_integrity,target_input_plan
selection=json.loads((task/'selected-release.json').read_text('utf-8'))
source=Path('C:/SpugHandoff/backend-log-src-20261102')
actual=subprocess.run(['git','rev-parse','HEAD'],cwd=source,capture_output=True,text=True,check=True).stdout.strip()
assert actual==selection['commit']
dirty=subprocess.run(['git','status','--porcelain','--untracked-files=no'],cwd=source,capture_output=True,text=True,check=True).stdout
assert not dirty,'Tracked source differs from selected commit'
with sqlite3.connect('file:C:/SpugHandoff/release/state/state.sqlite3?mode=ro',uri=True) as db:
    state=json.loads(db.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
migrations,_,_=migration_inputs(source)
targets={}
for env in ('test','prod','backup'):
    records=state['environments'][env]['ledgerRecords']
    historical_integrity(migrations,records)
    plan=target_input_plan(migrations,records,env)
    targets[env]=dict(actions=dict(Counter(i['action'] for i in plan['items'])),
        apply=[i['migrationId'] for i in plan['items'] if i['action']=='APPLY'])
report=dict(status='PASS',verification='static-only',commit=actual,targets=targets)
output=task/'full-input-plan-quartz-v2.json'
assert not output.exists(),'Preserve earlier evidence'
output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
