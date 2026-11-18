"""Exercise the compiled JAR offline before installing a locator correction."""
from pathlib import Path
import hashlib,json,sqlite3,subprocess,sys
repo=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(repo/'ops/spug/release-center'))
from backend_patch_build import pinned_runtime,verify_java
root=Path('C:/SpugHandoff/release')
with sqlite3.connect('file:'+str(root/'state/state.sqlite3').replace('\\','/')+'?mode=ro',uri=True) as db:
    state=json.loads(db.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
job=next(j for j in state['jobs'] if j['id']=='JOB-6c804e6c7f')
base=next(b for b in state['backendPatchBaselines'] if b['id']==job['payload']['baselineId'])
class Verifier:
    def manifest(self,tag):
        package=next(p for p in state['packages'] if p['releaseTag']==tag)
        path=Path(package['directory'])/'manifest.json'
        assert hashlib.sha256(path.read_bytes()).hexdigest()==package['manifestSha256']
        return package,json.loads(path.read_text('utf-8'))
    def run(self,args):
        result=subprocess.run(args,capture_output=True,timeout=180)
        assert result.returncode==0,'Offline Docker operation failed: '+args[1]
        return result.stdout
verifier=Verifier()
result=verify_java(verifier,job,Path(job['buildDirectory'])/'app.jar',pinned_runtime(verifier,base))
Path(__file__).with_name('offline-pinned-jar.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
