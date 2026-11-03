"""Only aggregate counts, never task contents or writes."""
from pathlib import Path
import json,sys,subprocess,concurrent.futures
sys.path.insert(0,'C:/SpugHandoff/release/source/ops/spug/release-center')
from intruoyi_runtime import Runtime,ssh_source_bytes
c=json.loads(Path('C:/SpugHandoff/release/executor.private.json').read_text('utf-8'));r=Runtime(c)
remote=Path('C:/SpugHandoff/release/source/ops/spug/release-center/intruoyi_remote.py').read_text('utf-8').split("if __name__ == '__main__':")[0]
script='''
sql(p,'DESCRIBE dcc_controlled_file_recognition_claim;')
sql(p,'DESCRIBE dcc_controlled_file_batch_recognition_task;')
counts={
 'terminalClaims':sql(p,"SELECT COUNT(*) FROM dcc_controlled_file_recognition_claim c INNER JOIN dcc_controlled_file_batch_recognition_task t ON t.id=c.claim_task_id AND t.tenant_id=c.tenant_id WHERE c.deleted=0 AND t.status IN ('COMPLETED','FAILED','STOPPED');"),
 'runningTasks':sql(p,"SELECT COUNT(*) FROM dcc_controlled_file_batch_recognition_task WHERE deleted=0 AND status='RUNNING';")}
print(json.dumps(counts))
'''
def read(env):
 p=r.profile(env);code=remote+'\np='+repr(p)+'\n'+script
 result=subprocess.run(['ssh',*r.ssh_options(),'root@'+p['host'],p['python']+' -'],input=ssh_source_bytes(code),capture_output=True,timeout=40)
 assert result.returncode==0,'Read-only startup inventory failed'
 return env,json.loads(result.stdout)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:result=dict(pool.map(read,['test','prod','backup']))
Path(__file__).with_name('startup-data-counts.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
