"""Read runtime scheduler age, installed JAR Quartz keys, and definition mismatch counts only."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json, subprocess, sys
live=Path('C:/SpugHandoff/release/source/ops/spug/release-center');sys.path.insert(0,str(live))
from intruoyi_runtime import Runtime,ssh_source_bytes
runtime=Runtime(json.loads(Path('C:/SpugHandoff/release/executor.private.json').read_text('utf-8')))
source=(live/'intruoyi_remote.py').read_text('utf-8').split("if __name__ == '__main__':")[0]
code=r'''
from pathlib import Path
import zipfile,time
container=inspect(p['backend']);result={}
def checkin():
    return sql(p,'SELECT SCHED_NAME,COUNT(*),MIN(ROUND(UNIX_TIMESTAMP()*1000-LAST_CHECKIN_TIME)),MAX(CHECKIN_INTERVAL) FROM qrtz_scheduler_state GROUP BY SCHED_NAME;').splitlines()
result['schedulerCheckinBefore']=checkin()
merged=container.get('GraphDriver',{}).get('Data',{}).get('MergedDir')
jar=Path(merged)/'yudao-server/app.jar' if merged else None
result['installedJarKeys']=[]
if jar and jar.is_file():
    with zipfile.ZipFile(str(jar)) as archive:
        for filename in ('application.yaml','application-dev.yaml','application-local.yaml'):
            member='BOOT-INF/classes/'+filename
            if member not in archive.namelist():continue
            parents=[]
            for line in archive.read(member).decode('utf-8').splitlines():
                match=re.match(r'^( *)([A-Za-z0-9_.-]+):\s*(.*?)\s*(?:#.*)?$',line)
                if not match:continue
                depth=len(match[1]);key=match[2];value=match[3].split('#')[0].strip()
                while parents and parents[-1][0]>=depth:parents.pop()
                full='.'.join([v for _,v in parents]+[key])
                if full in ('spring.quartz.auto-startup','spring.quartz.job-store-type','spring.quartz.properties.org.quartz.jobStore.isClustered','spring.autoconfigure.exclude'):
                    if full.endswith('exclude'):value='quartz-excluded' if 'QuartzAutoConfiguration' in value else 'other-exclusions'
                    elif value not in ('true','false','jdbc','memory'):value='<not-literal>'
                    result['installedJarKeys'].append(dict(file=filename,key=full,value=value))
                if not value:parents.append((depth,key))
result['definitionMismatchCounts']=sql(p,"SELECT COUNT(*),SUM(q.JOB_NAME IS NULL),SUM(t.TRIGGER_NAME IS NULL),SUM(c.TRIGGER_NAME IS NULL),SUM(COALESCE(c.CRON_EXPRESSION,'')<>j.cron_expression),SUM((j.status=2 AND t.TRIGGER_STATE NOT IN ('PAUSED','PAUSED_BLOCKED')) OR (j.status<>2 AND t.TRIGGER_STATE NOT IN ('WAITING','ACQUIRED','BLOCKED'))) FROM infra_job j LEFT JOIN qrtz_job_details q ON q.JOB_NAME=j.handler_name AND q.JOB_GROUP='DEFAULT' LEFT JOIN qrtz_triggers t ON t.SCHED_NAME=q.SCHED_NAME AND t.TRIGGER_NAME=j.handler_name AND t.TRIGGER_GROUP='DEFAULT' LEFT JOIN qrtz_cron_triggers c ON c.SCHED_NAME=t.SCHED_NAME AND c.TRIGGER_NAME=t.TRIGGER_NAME AND c.TRIGGER_GROUP=t.TRIGGER_GROUP WHERE j.deleted=b'0';")
time.sleep(8)
result['schedulerCheckinAfter']=checkin()
print(json.dumps(result))
'''
def read(env):
    p=runtime.profile(env)
    r=subprocess.run(['ssh',*runtime.ssh_options(),'root@'+p['host'],p['python']+' -'],input=ssh_source_bytes(source+'\np='+repr(p)+'\n'+code),capture_output=True,timeout=45)
    assert r.returncode==0,env+': read-only live Quartz inspection failed'
    return env,json.loads(r.stdout)
with ThreadPoolExecutor(max_workers=3) as pool:result=dict(pool.map(read,('test','prod','backup')))
output=Path(__file__).with_name('quartz-live-state.json');assert not output.exists()
output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
