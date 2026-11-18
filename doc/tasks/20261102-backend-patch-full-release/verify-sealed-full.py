"""Independently verify immutable full-package bytes and patch source inclusion."""
from pathlib import Path
import hashlib,json,sqlite3,tarfile
task=Path(__file__).parent
selection=json.loads((task/'selected-release.json').read_text('utf-8'))
with sqlite3.connect('file:C:/SpugHandoff/release/state/state.sqlite3?mode=ro',uri=True) as db:
    state=json.loads(db.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
job=next(j for j in state['jobs'] if j['id']==selection['fullReleaseTagBuildJobId'])
retry_job=None
if job['status']!='succeeded':
    resolution=job['resolution']
    assert job['status'] in ('failed','interrupted') and resolution['decision']=='retry'
    assert resolution['originalBuildJobId']==job['id']
    retry_job=next(j for j in state['jobs'] if j['id']==resolution['jobId'])
    assert retry_job['status']=='succeeded' and retry_job['action']=='resolve-task'
    assert retry_job['originalBuildJobId']==job['id'] and retry_job['releaseTag']==selection['fullReleaseTag']
    assert retry_job['result']['originalBuildJobId']==job['id']
assert job['buildWorktreeCleanup']['status']=='passed'
assert job['buildWorktreeCleanup']['physicalPathExists'] is False
package=next(p for p in state['packages'] if p['releaseTag']==selection['fullReleaseTag'])
folder=Path(package['directory'])
def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
assert sha(folder/'manifest.json')==package['manifestSha256']
assert sha(folder/'release.tar')==package['packageSha256']
manifest=json.loads((folder/'manifest.json').read_text('utf-8'))
assert manifest['gitCommit']==selection['commit']
assert manifest['releaseTag']==manifest['IMAGE_TAG']==selection['fullReleaseTag']
assert manifest['releaseSettings']['gxpAuditMode']=='DEVELOPMENT_DISABLED'
expected={'manifest.json':package['manifestSha256']}
for item in manifest['files']:
    assert item['name'] not in expected
    expected[item['name']]=item['sha256']
    assert sha(folder/item['name'])==item['sha256']
with tarfile.open(folder/'release.tar') as archive:
    members=archive.getmembers()
    assert all(member.isfile() and member.name in expected for member in members)
    assert len(members)==len(expected) and len(set(m.name for m in members))==len(expected)
    for member in members:
        assert hashlib.file_digest(archive.extractfile(member),'sha256').hexdigest()==expected[member.name]
infos=[json.loads((folder/(role+'-release-info.json')).read_text('utf-8')) for role in ('backend','frontend')]
assert infos[0]==infos[1] and infos[0]['sourceCommit']==selection['commit']
assert any('启动' in note and '日志' in note for note in infos[0]['changeSet']['gitChanges'])
contract=json.loads((folder/'backend-artifact-contract.json').read_text('utf-8'))
nas=Path(package['nasDirectory'])
assert sha(nas/'release.tar')==package['packageSha256']
assert sha(nas/'manifest.json')==package['manifestSha256']
report=dict(status='PASS',tag=package['releaseTag'],gitCommit=manifest['gitCommit'],
    packageBytes=(folder/'release.tar').stat().st_size,manifestMembers=len(expected),
    packageSha256=package['packageSha256'],manifestSha256=package['manifestSha256'],
    jarSha256=contract['jarSha256'],gxpAuditMode=manifest['releaseSettings']['gxpAuditMode'],
    sameSourceAsPatch=True,frontendBackendMetadataEqual=True,startupLogNoteVisibleInMetadata=True,
    buildWorktreeRemoved=True,nasOriginalVerified=True,originalBuildStatus=job['status'],
    verifiedOriginalPackageRetryJobId=retry_job['id'] if retry_job else None)
output=task/'sealed-full-verification.json';assert not output.exists()
output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
