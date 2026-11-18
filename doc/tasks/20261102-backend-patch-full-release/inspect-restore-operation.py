from pathlib import Path
import json,sys,subprocess,re
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'ops/spug/release-center'))
from intruoyi_runtime import Runtime
c=json.loads(Path('C:/SpugHandoff/release/executor.private.json').read_text('utf-8'))
r=Runtime(c);original=subprocess.run
def capture(*a,**kw):
    result=original(*a,**kw)
    if result.returncode:
        Path('C:/SpugHandoff/release/private/backend-patch-full-release-20261102/restore-inspection.stderr.private.log').write_bytes(result.stderr)
        err=result.stderr.decode('utf-8',errors='replace')
        print(json.dumps(dict(exitCode=result.returncode,errorTail=err[-1200:])))
    return result
subprocess.run=capture
result=r.call('test','inspect-operation',originalOperationId='OP-5d90b5b3daeaa7298553',originalJobId='JOB-fdd84f0df3')
Path(__file__).with_name('restore-operation-inspection.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
