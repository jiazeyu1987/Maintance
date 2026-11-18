"""Read-only independent verification of the selected immutable patch bytes."""
from pathlib import Path
import hashlib,json,sqlite3,sys,tarfile
root=Path('C:/SpugHandoff/release')
sys.path.insert(0,str(root/'source/ops/spug/release-center'))
from backend_patch_contract import validate_manifest
selection=json.loads(Path(__file__).with_name('selected-release.json').read_text('utf-8'))
with sqlite3.connect('file:'+str(root/'state/state.sqlite3')+'?mode=ro',uri=True) as db:
    state=json.loads(db.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
p=next(p for p in state['backendPatches'] if p['releaseTag']==selection['backendPatchTag'])
folder=Path(p['directory'])
def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
assert sha(folder/'manifest.json')==p['manifestSha256']
assert sha(folder/'release.tar')==p['packageSha256']
assert sha(folder/'app.jar')==p['jarSha256']
manifest=validate_manifest(json.loads((folder/'manifest.json').read_text('utf-8')))
assert manifest['gitCommit']==selection['commit'] and manifest['releaseTag']==selection['backendPatchTag']
with tarfile.open(folder/'release.tar') as archive:
    members=archive.getmembers()
    assert all(m.isfile() and m.name in ('app.jar','manifest.json','release-info.json') for m in members)
    assert len(members)==3
    assert hashlib.file_digest(archive.extractfile('app.jar'),'sha256').hexdigest()==p['jarSha256']
    assert hashlib.file_digest(archive.extractfile('manifest.json'),'sha256').hexdigest()==p['manifestSha256']
result=dict(status='PASS',tag=p['releaseTag'],gitCommit=p['gitCommit'],jarSha256=p['jarSha256'],
            jarBytes=(folder/'app.jar').stat().st_size,packageBytes=(folder/'release.tar').stat().st_size,
            packageSha256=p['packageSha256'],manifestSha256=p['manifestSha256'])
evidence=Path(__file__).with_name('sealed-patch-verification-'+p['releaseTag']+'.json')
assert not evidence.exists(),'Preserve earlier sealed-patch evidence'
evidence.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
