"""Prove the original clustered Quartz heartbeat continues without writing SQL."""
from pathlib import Path
import json,subprocess,sys
live=Path('C:/SpugHandoff/release/source/ops/spug/release-center');sys.path.insert(0,str(live))
from intruoyi_runtime import Runtime,ssh_source_bytes
phase=sys.argv[1];assert phase in ('patch','full')
runtime=Runtime(json.loads(Path('C:/SpugHandoff/release/executor.private.json').read_text('utf-8')))
profile=runtime.profile('prod')
source=(live/'intruoyi_remote.py').read_text('utf-8').split("if __name__ == '__main__':")[0]
code=source+'\nimport time\np='+repr(profile)+r'''
query='SELECT COUNT(*),MAX(LAST_CHECKIN_TIME),MAX(CHECKIN_INTERVAL),ROUND(UNIX_TIMESTAMP()*1000) FROM qrtz_scheduler_state;'
before=list(map(int,sql(p,query).split('\t')))
time.sleep(20)
after=list(map(int,sql(p,query).split('\t')))
assert before[0]>0 and after[0]>0 and after[1]>before[1]
assert 0<=after[3]-after[1]<max(60000,4*after[2])
print(json.dumps(dict(status='PASS',heartbeatAdvanced=True,intervalMs=after[2],ageMs=after[3]-after[1])))
'''
result=subprocess.run(['ssh',*runtime.ssh_options(),'root@'+profile['host'],profile['python']+' -'],input=ssh_source_bytes(code),capture_output=True,timeout=45)
assert result.returncode==0,'Original Quartz heartbeat verification failed'
report=json.loads(result.stdout)
output=Path(__file__).with_name('quartz-heartbeat-'+phase+'.json');assert not output.exists()
output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
