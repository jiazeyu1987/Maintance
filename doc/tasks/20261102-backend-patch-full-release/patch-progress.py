"""Read-only bounded progress without competing for the running operation lock."""
from pathlib import Path
import json,subprocess,sys
live=Path('C:/SpugHandoff/release/source/ops/spug/release-center');sys.path.insert(0,str(live))
from intruoyi_runtime import Runtime,ssh_source_bytes
config=json.loads(Path('C:/SpugHandoff/release/executor.private.json').read_text('utf-8'));runtime=Runtime(config)
env,tag,job=sys.argv[1:];p=runtime.profile(env)
remote=(live/'intruoyi_remote.py').read_text('utf-8').split("if __name__ == '__main__':")[0]
code=remote+'\nfrom pathlib import Path\np='+repr(p)+'\nroot=Path(p["stagingRoot"])/"backend-patches"/'+repr(tag)+'/'+repr(job)+'''
receipt=json.loads((root/'deployment.json').read_text()) if (root/'deployment.json').exists() else {}
fence=json.loads((root/'database-fence.json').read_text()) if (root/'database-fence.json').exists() else {}
containers={role:inspect(p[role]) for role in ('backend','frontend')}
print(json.dumps(dict(receipt={k:receipt.get(k) for k in ('status','errorType','databaseChanged')},
    fence={k:v for k,v in fence.items() if k in ('status','acquired','released','owner','jobId')},
    readOnly=sql(p,'SELECT @@global.read_only,@@global.super_read_only;'),
    containers={role:dict(running=v['State']['Running'],status=v['State']['Status'],startedAt=v['State']['StartedAt'],
    exitCode=v['State']['ExitCode'],health=v['State'].get('Health',{}).get('Status')) for role,v in containers.items()})))
'''
r=subprocess.run(['ssh',*runtime.ssh_options(),'root@'+p['host'],p['python']+' -'],input=ssh_source_bytes(code),capture_output=True,timeout=40)
assert r.returncode==0,'Progress read failed';print(r.stdout.decode('utf-8'))
