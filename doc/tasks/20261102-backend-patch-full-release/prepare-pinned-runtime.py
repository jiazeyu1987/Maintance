"""Restore the exact current runtime image from a verified NAS original."""
from pathlib import Path
import hashlib,json,shutil,sqlite3,subprocess,tarfile
root=Path('C:/SpugHandoff/release');private=root/'private/backend-patch-full-release-20261102'
config=json.loads((root/'executor.private.json').read_text('utf-8'))
with sqlite3.connect('file:'+str(root/'state/state.sqlite3').replace('\\','/')+'?mode=ro',uri=True) as db:
    state=json.loads(db.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
tag='2026-11-01-13-08-35'
package=next(p for p in state['packages'] if p['releaseTag']==tag)
nas=Path(config['nasPath'])/tag
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for data in iter(lambda:f.read(8*1024**2),b''):h.update(data)
    return h.hexdigest()
assert sha(nas/'manifest.json')==package['manifestSha256'],'NAS manifest changed'
manifest=json.loads((nas/'manifest.json').read_text('utf-8'))
expected='sha256:2b2160b4fba263ac7617f404fed767273ae6d21e9dbe59bfc2e2aaeb5d26c1f3'
assert manifest['images']['backend']['id']==expected,'NAS runtime differs from actual baseline'
assert sha(nas/'release.tar')==package['packageSha256'],'NAS original package changed'
destination=private/'pinned-runtime-images.tar'
if not destination.exists():
    with tarfile.open(nas/'release.tar','r:') as archive:
        member=archive.getmember('images.tar');assert member.isfile()
        with archive.extractfile(member) as src,destination.open('xb') as out:shutil.copyfileobj(src,out,8*1024**2)
item=next(i for i in manifest['files'] if i['name']=='images.tar')
assert sha(destination)==item['sha256'],'Runtime images archive changed'
runtime=manifest['images']['backend']
actual=subprocess.check_output(['docker','image','inspect','--format','{{.Id}}',runtime['name']]).decode().strip()
assert actual==runtime.get('localImageId',runtime['id']),'Loaded local immutable image differs'
with tarfile.open(destination,'r:') as archive:
    entries=json.load(archive.extractfile('manifest.json'))
    entry=next(e for e in entries if runtime['name'] in e.get('RepoTags',[]))
    assert 'sha256:'+hashlib.sha256(archive.extractfile(entry['Config']).read()).hexdigest()==expected
report=dict(status='passed',mainReleaseTag=tag,packageSha256=package['packageSha256'],
            manifestSha256=package['manifestSha256'],imagesArchiveSha256=item['sha256'],runtimeImageId=expected,localImageId=actual,
            source='verified-nas-original',remoteChanges=False)
Path(__file__).with_name('pinned-runtime.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
