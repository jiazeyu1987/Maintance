"""Read-only early check using the same committed migration contract as full builds."""
from pathlib import Path
from collections import Counter
import json,sqlite3,sys
repo=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(repo/'ops/spug/release-center'))
from intruoyi_build import migration_inputs,historical_integrity,target_input_plan
with sqlite3.connect('file:C:/SpugHandoff/release/state/state.sqlite3?mode=ro',uri=True) as db:
    state=json.loads(db.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
migrations,_,_=migration_inputs(Path('C:/SpugHandoff/backend-log-src-20261102'))
result={}
for env in ('test','prod','backup'):
    records=state['environments'][env]['ledgerRecords']
    historical_integrity(migrations,records)
    plan=target_input_plan(migrations,records,env)
    result[env]=dict(actions=dict(Counter(i['action'] for i in plan['items'])),
        apply=[i['migrationId'] for i in plan['items'] if i['action']=='APPLY'])
report=dict(status='PASS',readOnly=True,verification='static-only',commit='e5934b12e46064b01c8b5ad0b4c016229286c223',targets=result)
Path(__file__).with_name('next-full-inputs.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
