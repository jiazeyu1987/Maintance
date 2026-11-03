"""Read only effective boolean/job-store overrides; never emit private config."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json,subprocess,sys
live=Path('C:/SpugHandoff/release/source/ops/spug/release-center');sys.path.insert(0,str(live))
from intruoyi_runtime import Runtime,ssh_source_bytes
runtime=Runtime(json.loads(Path('C:/SpugHandoff/release/executor.private.json').read_text('utf-8')))
inspector=(live/'intruoyi_remote.py').read_text('utf-8').split("if __name__ == '__main__':")[0]
code=r'''
container=inspect(p['backend']);env=dict(v.split('=',1) for v in container['Config']['Env'])
keys={'spring.quartz.auto-startup','spring.quartz.job-store-type','yudao.local-job-control.startup-sync-enabled','yudao.local-job-control.enabled','intruoyi.release.maintenance'}
result={'overrides':[]}
def add(source,key,value):
    if key in keys:result['overrides'].append(dict(source=source,key=key,value=value if value in ('true','false','jdbc','memory') else '<non-boolean>'))
for key,value in env.items():add('environment',key.lower().replace('_','.'),value)
for key in ('ARGS','INTRUOYI_EXTRA_ARGS'):
    for match in re.finditer(r'--([a-zA-Z0-9_.-]+)=([^\s]+)',env.get(key,'')):add(key,match[1],match[2])
for mount in container['Mounts']:
    if mount['Destination'].endswith('.properties'):
        for line in Path(mount['Source']).read_text('utf-8').splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                key,value=line.split('=',1);add('mounted-properties',key.strip(),value.strip())
result['quartzTableNames']=sql(p,"SHOW TABLES LIKE '%QRTZ%';").splitlines()
print(json.dumps(result))
'''
def read(environment):
    p=runtime.profile(environment)
    result=subprocess.run(['ssh',*runtime.ssh_options(),'root@'+p['host'],p['python']+' -'],input=ssh_source_bytes(inspector+'\nfrom pathlib import Path\np='+repr(p)+'\n'+code),capture_output=True,timeout=40)
    assert result.returncode==0,environment+': Quartz configuration inventory failed'
    return environment,json.loads(result.stdout)
with ThreadPoolExecutor(max_workers=3) as pool:result=dict(pool.map(read,('test','prod','backup')))
output=Path(__file__).with_name('quartz-runtime-inventory.json');assert not output.exists()
output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
