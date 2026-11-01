import hashlib
import json
from pathlib import Path
import sqlite3
import tarfile
from publication_proof import verify_publication

task=Path(__file__).parent
candidate=json.loads((task/'candidate.json').read_text('utf-8'))
with sqlite3.connect('file:C:/SpugHandoff/release/state/state.sqlite3?mode=ro',uri=True) as db:
    state=json.loads(db.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
job=next(j for j in state['jobs'] if j['id']==candidate['buildJobId'])
package=next(p for p in state['packages'] if p['releaseTag']==candidate['releaseTag'])
verify_publication(state,candidate,package)
folder=Path(package['directory'])

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()

manifest=json.loads((folder/'manifest.json').read_text('utf-8'))
assert manifest['gitCommit']==candidate['sourceCommit']==package['gitCommit']
assert manifest['IMAGE_TAG']==manifest['releaseTag']==candidate['releaseTag']
assert manifest['releaseSettings']['gxpAuditMode']=='DEVELOPMENT_DISABLED'
for base in (folder,Path(package['nasDirectory'])):
    assert digest(base/'release.tar')==package['packageSha256']
    assert digest(base/'manifest.json')==package['manifestSha256']
for row in manifest['files']:
    assert digest(folder/row['name'])==row['sha256']
with tarfile.open(folder/'release.tar','r:') as archive:
    names=archive.getnames()
    assert len(names)==len(set(names)) and set(names)=={'manifest.json'}|{r['name'] for r in manifest['files']}
    assert hashlib.sha256(archive.extractfile('manifest.json').read()).hexdigest()==package['manifestSha256']
    for row in manifest['files']:
        with archive.extractfile(row['name']) as stream:
            assert hashlib.file_digest(stream,'sha256').hexdigest()==row['sha256']
name='20261101_dcc_source_governance_all_environments'
entry=next(m for m in manifest['migrations'] if m['migrationId']==name)
assert set(entry['allowedEnvironments'])=={'test','prod','backup'}
assert entry['sha256']=='0a5c2494efe4b2dd41497180b9b52a3a045137e1b63743593512f5717d9fc7d5'
readiness=json.loads((folder/'migration-readiness.json').read_text('utf-8'))
plans={}
for env,plan in readiness['targets'].items():
    assert plan['status']=='passed'
    pending=[r['migrationId'] for r in plan['items'] if r['action']=='APPLY']
    assert pending==[name], 'Unexpected pending migration; review before publishing'
    plans[env]=pending
artifact=json.loads((folder/'backend-artifact-contract.json').read_text('utf-8'))
assert artifact['status']=='passed'
cleanup=job['buildWorktreeCleanup']
assert not Path(job['buildWorktree']).exists(), 'Frozen build checkout was not removed'
result=dict(status='PASS',releaseTag=candidate['releaseTag'],sourceCommit=manifest['gitCommit'],
    packageBytes=(folder/'release.tar').stat().st_size,packageSha256=package['packageSha256'],manifestSha256=package['manifestSha256'],
    manifestFileCount=len(manifest['files']),localAndNasOriginalMatch=True,allArchiveMembersVerified=True,
    pendingMigrations=plans,gxpAuditMode='DEVELOPMENT_DISABLED',backendArtifactContract=artifact,
    buildWorktreeCleanup=cleanup)
(task/'sealed-package-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
