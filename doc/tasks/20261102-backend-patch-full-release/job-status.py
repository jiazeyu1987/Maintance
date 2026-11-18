"""Bounded, read-only progress; raw command logs remain private."""
import json,sqlite3,sys
from pathlib import Path
root=Path('C:/SpugHandoff/release')
with sqlite3.connect('file:'+str(root/'state/state.sqlite3').replace('\\','/')+'?mode=ro',uri=True) as db:
    state=json.loads(db.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
jobs=state['jobs'][:1] if len(sys.argv)==1 else [j for j in state['jobs'] if j['id']==sys.argv[1]]
keys=('id','action','status','target','releaseTag','currentStep','error','result','buildWorktree','buildWorktreeCleanup','backendJavaCompatibility')
for job in jobs:
    report={key:job.get(key) for key in keys if key in job}
    if isinstance(report.get('result'),dict):report['resultKeys']=sorted(report.pop('result'))
    if job['status']!='running':
        Path(__file__).with_name('status-'+job['id']+'.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True))
