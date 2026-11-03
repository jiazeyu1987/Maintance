"""Compile a reconstructed delivery payload only; never execute the agent."""
from pathlib import Path
import base64,json,re,sqlite3,subprocess,sys
from unittest.mock import patch
live=Path('C:/SpugHandoff/release/source/ops/spug/release-center');sys.path.insert(0,str(live))
from intruoyi_runtime import Runtime
root=Path('C:/SpugHandoff/release');private=root/'private/backend-patch-full-release-20261102'
runtime=Runtime(json.loads((root/'executor.private.json').read_text('utf-8')))
with sqlite3.connect('file:'+str(root/'state/state.sqlite3')+'?mode=ro',uri=True) as c:
    state=json.loads(c.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
job=next(j for j in state['jobs'] if j['id']=='JOB-5bcd73ebab')
package=next(p for p in state['backendPatches'] if p['releaseTag']==job['releaseTag'])
manifest=json.loads((Path(package['directory'])/'manifest.json').read_text('utf-8'))
archive=dict(sha256=package['packageSha256'],manifestSha256=package['manifestSha256'],bytes=(Path(package['directory'])/'release.tar').stat().st_size)
with patch('intruoyi_runtime.subprocess.run',return_value=subprocess.CompletedProcess([],0,b'{"ok":true,"result":null}',b'')) as intercepted:
    runtime.call('test','backend-patch-deploy',manifest=manifest,archive=archive,origin=job['backendOrigin'],
                 operationId='OP-8c8f5f80b36442eeb695',workflowJobId=job['id'])
delivery=intercepted.call_args.kwargs['input']
source=base64.b64decode(delivery.split(b"base64.b64decode('",1)[1].split(b"'",1)[0])
compile(source,'reconstructed-agent','exec')
# The transmitted payload compiles the agent source into a code object only.
probe=delivery.replace(b'exec(compile(',b'compile(',1)
assert probe.endswith(b",'<release-agent>','exec'))\n")
probe=probe[:-2]+b'\nprint("TRANSPORT_COMPILE_PASS")\n'
compile(probe,'transport-probe','exec')
results=[]
for number in range(3):
    result=subprocess.run(intercepted.call_args.args[0],input=probe,capture_output=True,timeout=40)
    path=private/('transport-compile-'+str(number)+'.private.log');assert not path.exists()
    path.write_bytes(result.stdout+b'\n'+result.stderr)
    results.append(dict(exitCode=result.returncode,compilePass=result.stdout.strip()==b'TRANSPORT_COMPILE_PASS',
                        errorTypes=re.findall(r'\b(?:SyntaxError|UnicodeDecodeError|BrokenPipeError|ConnectionResetError)\b',result.stderr.decode('utf-8',errors='replace'))))
report=dict(status='PASS' if all(v['compilePass'] for v in results) else 'FAIL',sourceBytes=len(source),deliveryBytes=len(probe),
            executedAgent=False,results=results)
Path(__file__).with_name('transport-compile-proof.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
