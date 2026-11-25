"""Assemble page evidence only after every raw observation has an explicit review."""
import hashlib,json,re,sys
from pathlib import Path
task=Path(__file__).resolve().parent
root=Path('C:/SpugHandoff/release/private/intruoyi-fenbeitong-test-prod-20261125')
env,tag,commit,job_id=sys.argv[1:]
assert env in ('test','prod','prod-maintenance')
state=json.loads((root/'state.private.json').read_text(encoding='utf-8'))
job=next(j for j in state['jobs'] if j['id']==job_id)
package=next(p for p in state['packages'] if p['releaseTag']==tag)
assert job['status']=='succeeded' and job['releaseTag']==tag
notes=json.loads((task/(env+'-observation-review.json')).read_text(encoding='utf-8'))
assert notes['releaseTag']==tag and notes['reviewer']=='Codex'
def clean(v):
    if isinstance(v,str):
        v=re.sub(r'(https?://[^\s"<>?]+)\?[^\s"<>]*',r'\1?<redacted>',v)
        return re.sub(r'(/user/avatar/)[^\s"<>]+',r'\1<redacted>',v)
    if isinstance(v,list):return [clean(x) for x in v]
    if isinstance(v,dict):return {k:clean(x) for k,x in v.items()}
    return v
reports=[]
for name,required in [('menu',{'real-login','menu-navigation-and-real-data','page-version-and-changelog'}),
                      ('fenbeitong',{'real-login','runtime-public-url','real-ticket-and-authenticated-iframe','visible-version-and-changelog'})]:
    p=root/env/(name+'-page.private.json')
    v=json.loads(p.read_text(encoding='utf-8'))
    digest=hashlib.sha256(p.read_bytes()).hexdigest()
    review=notes['probes'][name]
    assert review['evidenceSha256']==digest and len(review['observations'])==len(v['observations'])
    assert v['environment']==env and v['releaseTag']==tag and not v.get('error')
    assert v['status'] in ('PASS','NEEDS_REVIEW')
    assert required<={x['name'] for x in v['checks'] if x['status']=='PASS'}
    versions=[x for x in v['checks'] if x.get('sourceCommit')]
    assert versions and all(x['sourceCommit']==commit and x['releaseTag']==tag for x in versions)
    observations=[]
    for i,(event,note) in enumerate(zip(v['observations'],review['observations'])):
        assert note['index']==i and note['disposition']=='nonblocking'
        assert all(note.get(k) for k in ('attribution','impactEvidence','owner'))
        observations.append(dict(id=name+'-'+str(i),rawEvent=clean(event),**note))
    pending=v.get('inFlight',[])
    pending_notes=review.get('pendingRequests',[])
    assert len(pending)==len(pending_notes), 'Unreviewed pending requests at observation window end'
    pending_reports=[]
    for i,(event,note) in enumerate(zip(pending,pending_notes)):
        assert note['index']==i and note['disposition']=='out-of-scope-unverified'
        assert all(note.get(k) for k in ('attribution','impactEvidence','owner'))
        pending_reports.append(dict(rawEvent=clean(event),**note))
    script=task/('menu-page-check.cjs' if name=='menu' else 'page-check.cjs')
    reports.append(dict(probe=name,evidenceSha256=digest,script=script.name,scriptSha256=hashlib.sha256(script.read_bytes()).hexdigest(),
        observationWindow=[v['startedAt'],v['endedAt']],checks=clean(v['checks']),observations=observations,
        pendingRequestsAtWindowEnd=pending_reports))
result=dict(environment=env,releaseTag=tag,sourceCommit=commit,packageSha256=package['packageSha256'],jobId=job_id,
    reviewer='Codex',status='PASS_WITH_OBSERVATIONS' if any(v['observations'] for v in reports) else 'PASS',
    scope=dict(verified=['real frontend login','schedule menu and actual list response (including actual empty state)',
        'Fenbeitong status URL, issued ticket and authenticated helper iframe','visible version and nonempty changelog'],
        notVerified=['Fenbeitong voucher synchronization or accounting writes','workbench context initialization and source registry loading','full business E2E']),
    blockers=[],reports=reports)
(task/(env+'-page-acceptance.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(environment=env,status=result['status'],releaseTag=tag,observations=sum(len(v['observations']) for v in reports)),ensure_ascii=False))
