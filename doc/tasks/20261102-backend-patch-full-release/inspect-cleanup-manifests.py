"""Read only catalog and staged manifest identities; never repair old evidence."""
from pathlib import Path
import hashlib,json,sqlite3,subprocess,sys
root=Path('C:/SpugHandoff/release');task=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'source/ops/spug/release-center'))
from intruoyi_runtime import Runtime,ssh_source_bytes
import post_release_cleanup
config=json.loads((root/'executor.private.json').read_text('utf-8'));runtime=Runtime(config)
with sqlite3.connect('file:'+str(root/'state/state.sqlite3').replace('\\','/')+'?mode=ro',uri=True) as db:state=json.loads(db.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
class Catalog:
    c=config
    def read(self,tag,key):
        package=next(p for p in state[key] if p['releaseTag']==tag)
        path=Path(package['directory'])/'manifest.json';assert hashlib.sha256(path.read_bytes()).hexdigest()==package['manifestSha256']
        return package,json.loads(path.read_text('utf-8'))
    def manifest(self,tag):return self.read(tag,'packages')
    def frontend_package(self,tag):return self.read(tag,'frontendPatches')
    def backend_package(self,tag):return self.read(tag,'backendPatches')
entries=post_release_cleanup.resource_entries(Catalog(),state,'test')
rows=[]
for entry in entries:
    tag=entry['manifest']['releaseTag']
    if entry.get('kind'):relative=entry['kind']+'es/'+tag+'/'+entry['deploymentJobId']
    elif entry.get('attempt'):relative='attempts/'+entry['attempt']+'/'+tag
    else:relative=tag
    rows.append(dict(relative=relative,releaseTag=tag,expected=entry['manifestSha256']))
profile=runtime.profile('test')
code='from pathlib import Path\nimport hashlib,json\nbase=Path('+repr(profile['stagingRoot'])+')\nrows='+repr(rows)+'\n'+r'''
mismatches=[]
for row in rows:
    folder=base/row['relative']
    if not folder.exists():continue
    marker=folder/'manifest.json'
    actual=hashlib.sha256(marker.read_bytes()).hexdigest() if marker.is_file() else None
    if actual!=row['expected']:mismatches.append(dict(relative=row['relative'],releaseTag=row['releaseTag'],markerExists=marker.is_file(),actual=actual,expected=row['expected']))
print(json.dumps(mismatches))
'''
result=subprocess.run(['ssh',*runtime.ssh_options(),'root@'+profile['host'],profile['python']+' -'],input=ssh_source_bytes(code),capture_output=True,timeout=60)
assert result.returncode==0,'Staged manifest inspection failed'
proof=json.loads(result.stdout);(task/'cleanup-manifest-evidence.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8');print(json.dumps(proof))
