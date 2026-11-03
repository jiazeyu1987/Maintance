"""Use the existing complete read-only structure contract without installing UI."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json,subprocess,sys
task=Path(__file__).parent;repo=task.parents[2]
live=Path('C:/SpugHandoff/release/source/ops/spug/release-center');sys.path.insert(0,str(live))
from intruoyi_runtime import Runtime,ssh_source_bytes
sys.path.insert(0,str(repo/'ops/spug/release-center'))
import database_versions as contract
config=json.loads(Path('C:/SpugHandoff/release/executor.private.json').read_text('utf-8'));runtime=Runtime(config)
inspector=(live/'intruoyi_remote.py').read_text('utf-8').split("if __name__ == '__main__':")[0]
code_contract=(repo/'ops/spug/release-center/database_versions.py').read_text('utf-8')
def read(env):
    profile=runtime.profile(env)
    code='import types,sys\nr=types.ModuleType("r")\nexec('+repr(inspector)+',r.__dict__)\n'+code_contract+'\nprint(json.dumps(read_database(r,'+repr(profile)+')))\n'
    result=subprocess.run(['ssh',*runtime.ssh_options(),'root@'+profile['host'],profile['python']+' -'],input=ssh_source_bytes(code),capture_output=True,timeout=90)
    assert result.returncode==0,env+': metadata read failed'
    return env,json.loads(result.stdout)
with ThreadPoolExecutor(max_workers=3) as pool:targets=dict(pool.map(read,('test','prod','backup')))
comparison=contract.compare_targets(targets)
report=dict(algorithm=contract.SCHEMA_VERSION,targets=contract.public_targets(targets),comparisons=comparison)
phase=sys.argv[1];assert phase in ('before','patch','full')
output=task/('database-'+phase+'.json');assert not output.exists(),'Preserve original evidence'
output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(counts={e:v['schema']['counts'] for e,v in targets.items()},comparisons=comparison)))
assert all(p['schemaEqual'] for p in comparison),'Actual structure differs'
assert all(v['stable'] and v['migrations']['healthy'] for v in targets.values()),'Unstable structure or unhealthy migration history'
if phase=='patch':
    before=json.loads((task/'database-before.json').read_text('utf-8'))
    for env,value in report['targets'].items():
        assert value['schema']['sha256']==before['targets'][env]['schema']['sha256'],env+': patch changed structure'
        assert value['migrations']==before['targets'][env]['migrations'],env+': patch changed own migration history'
