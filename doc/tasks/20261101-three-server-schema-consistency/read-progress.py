"""Read local release history without emitting private configuration or logs."""
import json
from pathlib import Path
import sqlite3
import sys

dbpath=Path('C:/SpugHandoff/release/state/state.sqlite3')
with sqlite3.connect('file:'+str(dbpath)+'?mode=ro',uri=True) as db:
    state=json.loads(db.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
target=sys.argv[1] if len(sys.argv)>1 else None
jobs=[j for j in state['jobs'] if not target or j.get('releaseTag')==target or j['id']==target]
result=dict(jobs=[{k:j.get(k) for k in ('id','action','releaseTag','status','currentStep','createdAt','startedAt','finishedAt')} for j in jobs[:8]])
if len(jobs)==1 and jobs[0]['action']=='check-prerequisites':
    report=jobs[0].get('result',{})
    result['checks']=[{k:c.get(k) for k in ('id','status','detail')} for c in report.get('checks',[])]
    if jobs[0]['status'] in ('succeeded','failed'):
        (Path(__file__).parent/(jobs[0]['id']+'-prerequisites.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if target:
    package=next((p for p in state['packages'] if p['releaseTag']==target),None)
    if package:
        result['package']={k:package.get(k) for k in ('releaseTag','stage','commit','packageSha256','manifestSha256')}
print(json.dumps(result))
