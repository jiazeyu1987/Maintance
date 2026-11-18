"""Keep raw logs private; report only Java exception types and application frames."""
from pathlib import Path
import json,re,subprocess,sys
live=Path('C:/SpugHandoff/release/source/ops/spug/release-center');sys.path.insert(0,str(live))
from intruoyi_runtime import Runtime
c=json.loads(Path('C:/SpugHandoff/release/executor.private.json').read_text('utf-8'));runtime=Runtime(c)
env=sys.argv[1];p=runtime.profile(env)
phase=sys.argv[2] if len(sys.argv)>2 else ''
assert not phase or re.fullmatch('[a-z0-9-]+',phase)
suffix=('-'+phase) if phase else ''
r=subprocess.run(['ssh',*runtime.ssh_options(),'root@'+p['host'],'docker logs '+p['backend']],capture_output=True,timeout=30)
assert r.returncode==0
raw=r.stdout+b'\n'+r.stderr
output=Path('C:/SpugHandoff/release/private/backend-patch-full-release-20261102/'+env+suffix+'-startup.private.log')
assert not output.exists(),'Preserve earlier failure evidence'
output.write_bytes(raw)
log=raw.decode('utf-8',errors='replace')
summary=dict(exceptionTypes=sorted(set(re.findall(r'\b(?:[a-z_][\w]*\.)+[A-Z][\w]*(?:Exception|Error)\b',log))),
    applicationFrames=list(dict.fromkeys(re.findall(r'\bat (cn\.iocoder\.yudao\.[\w.$]+\([\w.]+:\d+\))',log)))[:35],
    signals={key:bool(re.search(pattern,log,re.I)) for key,pattern in dict(readOnly='super.read.only|read.only option|ERROR 1290',
      writeAttempt='INSERT INTO|UPDATE .*SET|CREATE TABLE|ALTER TABLE',missingConfig='Could not resolve placeholder',
      permission='Access denied|Permission denied',startupFailed='APPLICATION FAILED TO START|Application run failed').items()})
Path(__file__).with_name('startup-failure-'+env+suffix+'.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary))
