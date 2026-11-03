"""Read-only, independent verification of the bound later backend restoration."""
import hashlib,json,sqlite3,sys
from pathlib import Path
from types import SimpleNamespace
root=Path('C:/SpugHandoff/release')
repo=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root/'source/ops/spug/release-center'))
from intruoyi_runtime import Runtime
sys.path.insert(0,str(repo/'ops/spug/release-center'))
# Load the candidate only, retaining the installed Runtime's private variant.
import importlib.util
spec=importlib.util.spec_from_file_location('candidate_interruption',repo/'ops/spug/release-center/interruption.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
from backend_patch import BackendPatchMixin
class Reader(BackendPatchMixin):pass
reader=Reader();reader.c=json.loads((root/'executor.private.json').read_text('utf-8'))
reader.runtime=Runtime(reader.c)
with sqlite3.connect('file:'+str(root/'state/state.sqlite3').replace('\\','/')+'?mode=ro',uri=True) as db:
    reader.state=json.loads(db.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
original=next(j for j in reader.state['jobs'] if j['id']=='JOB-fdd84f0df3')
proof=module.backend_restoration_proof(reader,original)
assert proof
actual=proof['observation']
assert actual['backendHealth']=='UP' and actual['frontendHttpStatus']==200
assert actual['gxpAuditMode']=='DEVELOPMENT_DISABLED' and actual['backendPatchTag'] is None
evidence=dict(status='PASS',originalJobId=original['id'],restoredBy=proof['restoredBy'],
    restorationOperationId=proof['restorationOperationId'],releaseTag=actual['releaseTag'],
    jarSha256=actual['backendJarSha256'],schemaSha256=actual['schemaSha256'],ledgerSha256=actual['ledgerSha256'])
Path(__file__).with_name('restoration-proof.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
print(json.dumps(evidence))
