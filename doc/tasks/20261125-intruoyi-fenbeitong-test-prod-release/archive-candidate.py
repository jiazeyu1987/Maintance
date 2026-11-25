"""Retain the blocked candidate's evidence before evaluating a new release."""
import hashlib,json,shutil
from pathlib import Path
task=Path(__file__).resolve().parent
root=Path('C:/SpugHandoff/release/private/intruoyi-fenbeitong-test-prod-20261125')
tag='2026-11-26-00-12-02'
page=json.loads((root/'test/fenbeitong-page.private.json').read_text(encoding='utf-8'))
runtime=json.loads((root/'test-runtime-verification.json').read_text(encoding='utf-8'))
assert page['status']=='BLOCKED' and runtime['releaseTag']==tag
dest=root/'candidate-history'/tag; assert not dest.exists(); dest.mkdir(parents=True)
for p in root.iterdir():
    if p.name=='candidate-history':continue
    if p.is_file() and (p.name.startswith('test') or p.name=='state.private.json'):
        shutil.copy2(p,dest/p.name)
    elif p.name=='test' and p.is_dir():shutil.copytree(p,dest/p.name)
report=dict(status='BLOCKED',environment='test',releaseTag=tag,sourceCommit=runtime['gitCommit'],
    packageSha256=runtime['packageSha256'],jobId=runtime['deploymentJob'],runtimeStatus='PASS',
    scope=['real-login','schedule-menu-read','visible-version-and-changelog','fenbeitong-authenticated-iframe'],
    blocker=dict(path='/auth/callback',status=503,rootCause='ERP ticket lacked issuing tenant; tenant configuration lookup failed'),
    rawObservationCount=len(page['observations']),observationWindow=[page['startedAt'],page['endedAt']],
    evidenceSha256=hashlib.sha256((dest/'test/fenbeitong-page.private.json').read_bytes()).hexdigest(),
    disposition='Not marked tested; not promoted to production. Replaced by a new committed release after tenant fix.')
(task/'blocked-candidate.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status='PASS',archivedTag=tag,contractReceipts=[{k:v.get(k) for k in ('phase','status','releaseTag')} for v in runtime['databaseContractReceipts']]),ensure_ascii=False))
