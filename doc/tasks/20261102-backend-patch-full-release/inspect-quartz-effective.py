"""Read only allowlisted effective profile/Quartz inputs and scheduler log signals."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json, subprocess, sys
live = Path('C:/SpugHandoff/release/source/ops/spug/release-center')
sys.path.insert(0, str(live))
from intruoyi_runtime import Runtime, ssh_source_bytes
runtime = Runtime(json.loads(Path('C:/SpugHandoff/release/executor.private.json').read_text('utf-8')))
inspector = (live/'intruoyi_remote.py').read_text('utf-8').split("if __name__ == '__main__':")[0]
code = r'''
container=inspect(p['backend']); env=dict(v.split('=',1) for v in container['Config']['Env'])
allowed={'spring.profiles.active','spring.quartz.auto-startup','spring.quartz.job-store-type','spring.quartz.properties.org.quartz.jobStore.isClustered','spring.quartz.properties.org.quartz.scheduler.instanceName','yudao.local-job-control.enabled','yudao.local-job-control.startup-sync-enabled'}
result={'inputs':[], 'schedulerSignals':[]}
def add(source,key,value):
    if key in allowed:
        if not re.fullmatch(r'[A-Za-z0-9_,.\-]+',str(value)):value='<redacted-non-token>'
        result['inputs'].append(dict(source=source,key=key,value=value))
for key,value in env.items():add('environment',key.lower().replace('_','.'),value)
for key in ('ARGS','INTRUOYI_EXTRA_ARGS','JAVA_OPTS','JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS'):
    for match in re.finditer(r'(?:--|-D)([a-zA-Z0-9_.-]+)=([^\s]+)',env.get(key,'')):add(key,match[1],match[2])
for arg in container['Config'].get('Cmd') or []:
    for match in re.finditer(r'--([a-zA-Z0-9_.-]+)=([^\s]+)',str(arg)):add('command',match[1],match[2])
for mount in container['Mounts']:
    if mount['Destination'].endswith('.properties'):
        for line in Path(mount['Source']).read_text('utf-8').splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                key,value=line.split('=',1);add('mounted-properties',key.strip(),value.strip())
logs=subprocess.run(['docker','logs','--tail','1800',p['backend']],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
for line in (logs.stdout+b'\n'+logs.stderr).decode('utf-8',errors='strict').splitlines():
    for marker in ('NOT STARTED.', 'STANDBY MODE.', 'Scheduler started.', 'Starting Quartz Scheduler', 'Scheduler quartzScheduler_$_', 'Scheduler localScheduler_$_'):
        if marker in line:
            result['schedulerSignals'].append(marker)
result['schedulerSignals']=sorted(set(result['schedulerSignals']))
result['schema']={table:sql(p,'DESCRIBE `'+table+'`;').splitlines() for table in ('infra_job','qrtz_job_details','qrtz_triggers','qrtz_cron_triggers','qrtz_scheduler_state')}
result['counts']={table:int(sql(p,'SELECT COUNT(*) FROM `'+table+'`;')) for table in result['schema']}
print(json.dumps(result))
'''
def read(environment):
    p=runtime.profile(environment)
    result=subprocess.run(['ssh',*runtime.ssh_options(),'root@'+p['host'],p['python']+' -'],input=ssh_source_bytes(inspector+'\nfrom pathlib import Path\np='+repr(p)+'\n'+code),capture_output=True,timeout=45)
    if result.returncode:
        private=Path('C:/SpugHandoff/release/private/backend-patch-full-release-20261102')/('quartz-effective-'+environment+'.private.log')
        private.write_bytes(result.stderr)
        import re
        kind=re.findall(rb'^([A-Za-z]+(?:Error|Exception)):',result.stderr,re.M)
        raise AssertionError(environment+': Quartz allowlisted inventory failed, '+(kind[-1].decode('ascii') if kind else 'unknown error'))
    return environment,json.loads(result.stdout)
with ThreadPoolExecutor(max_workers=3) as pool: result=dict(pool.map(read,('test','prod','backup')))
output=Path(__file__).with_name('quartz-effective-complete-inventory.json');assert not output.exists()
output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({env:{k:v for k,v in data.items() if k!='schema'} for env,data in result.items()}))
