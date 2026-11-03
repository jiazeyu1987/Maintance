"""Read only local job timestamps; omit configuration and logs."""
from pathlib import Path
import json,sqlite3
task=Path(__file__).resolve().parent
root=Path('C:/SpugHandoff/release')
with sqlite3.connect('file:'+str(root/'state/state.sqlite3').replace('\\','/')+'?mode=ro',uri=True) as db:
    state=json.loads(db.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
jobs=[]
for job in state['jobs']:
    if job.get('releaseTag')=='2026-11-03-12-15-42' or (job['action'].startswith('backend-patch-') and job.get('createdAt','')>='2026-11-02'):
        row={k:job.get(k) for k in ('id','action','status','target','releaseTag')}
        row['times']={k:v for k,v in job.items() if k.lower().endswith(('at','time')) and isinstance(v,(str,int,float))}
        if job.get('postReleaseCleanup'):
            row['cleanup']={k:job['postReleaseCleanup'].get(k) for k in ('status','startedAt','finishedAt')}
        jobs.append(row)
report=dict(jobs=jobs)
(task/'timing-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
