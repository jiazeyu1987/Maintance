"""Read-only check of additional objects included in the runtime schema fingerprint."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys

task=Path(__file__).parent
sources=Path('C:/SpugHandoff/release/source/ops/spug/release-center')
sys.path.insert(0,str(sources))
from intruoyi_runtime import Runtime
config=json.loads(Path('C:/SpugHandoff/release/executor.private.json').read_text('utf-8'))
runtime=Runtime(config)
queries=dict(
    triggers='SELECT TRIGGER_NAME,EVENT_MANIPULATION,EVENT_OBJECT_TABLE,ACTION_TIMING,ACTION_STATEMENT,SQL_MODE FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA=DATABASE() ORDER BY TRIGGER_NAME;',
    routines='SELECT ROUTINE_NAME,ROUTINE_TYPE,ROUTINE_DEFINITION,SQL_MODE FROM information_schema.ROUTINES WHERE ROUTINE_SCHEMA=DATABASE() ORDER BY ROUTINE_NAME;',
    events='SELECT EVENT_NAME,STATUS,EVENT_DEFINITION FROM information_schema.EVENTS WHERE EVENT_SCHEMA=DATABASE() ORDER BY EVENT_NAME;')
source=(sources/'intruoyi_remote.py').read_text('utf-8').split("if __name__ == '__main__':")[0]
def collect(env):
    p=runtime.profile(env)
    code=source+'\nprofile='+repr(p)+'\nqueries='+repr(queries)+"\nprint(json.dumps({k:sql(profile,v) for k,v in queries.items()}))\n"
    r=subprocess.run(['ssh',*runtime.ssh_options(),'root@'+p['host'],shlex.quote(p['python'])+' -'],input=code.encode(),capture_output=True,timeout=120)
    assert r.returncode==0, env+' read-only schema collection failed'
    return env,json.loads(r.stdout)
with ThreadPoolExecutor(max_workers=3) as pool:
    values=dict(pool.map(collect,['test','prod','backup']))
matching=all(v==values['test'] for v in values.values())
report=dict(status='PASS' if matching else 'FAIL',time=datetime.now(timezone.utc).isoformat(),mutations=False,
    objects={e:{k:dict(empty=not value,sha256=hashlib.sha256(value.encode()).hexdigest()) for k,value in v.items()} for e,v in values.items()},identical=matching)
(task/'programmable-schema-before.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
assert matching, 'Programmable schema differs; inspect before deployment'
