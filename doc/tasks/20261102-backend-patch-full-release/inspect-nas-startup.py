"""Read-only schema/count/boolean startup inventory; never output task rows or configuration values."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json,subprocess,sys
live=Path('C:/SpugHandoff/release/source/ops/spug/release-center');sys.path.insert(0,str(live))
from intruoyi_runtime import Runtime,ssh_source_bytes
r=Runtime(json.loads(Path('C:/SpugHandoff/release/executor.private.json').read_text('utf-8')))
remote=(live/'intruoyi_remote.py').read_text('utf-8').split("if __name__ == '__main__':")[0]
script=r'''
import re
from pathlib import Path
tables=['dcc_controlled_file_nas_transfer_task','dcc_controlled_file_nas_transfer_task_item','dcc_nas_control_audit_task','showroom_product_cover_batch_task','showroom_product_cover_batch_task_item']
counts={}
for table in tables:
 columns={row.split('\t')[0] for row in sql(p,'DESCRIBE '+table+';').splitlines()}
 assert {'status','deleted'}<=columns
 counts[table]=sql(p,"SELECT COUNT(*) FROM "+table+" WHERE deleted=0 AND status='RUNNING';")
backend=inspect(p['backend'])
text='\n'.join(backend['Config'].get('Env',[]))+'\n'+' '.join(backend['Config'].get('Cmd',[]))
for mount in backend['Mounts']:
 if mount['Destination'].endswith('.properties'):text+='\n'+Path(mount['Source']).read_text('utf-8')
keys=['dcc-nas-transfer-enabled','dcc-nas-control-audit-enabled','showroom-product-cover-batch-resume-enabled','startup-sync-enabled']
flags={key:re.findall(r'(?:yudao\.local-job-control\.)?'+re.escape(key)+r'\s*[=:]\s*(true|false)',text,re.I) for key in keys}
print(json.dumps(dict(runningCounts=counts,explicitBooleanOverrides=flags)))
'''
def read(env):
 p=r.profile(env)
 v=subprocess.run(['ssh',*r.ssh_options(),'root@'+p['host'],p['python']+' -'],input=ssh_source_bytes(remote+'\np='+repr(p)+'\n'+script),capture_output=True,timeout=45)
 assert v.returncode==0,'Read-only NAS startup inventory failed'
 return env,json.loads(v.stdout)
with ThreadPoolExecutor(max_workers=3) as pool:report=dict(pool.map(read,['test','prod','backup']))
output=Path(__file__).with_name('all-recovery-startup-inventory.json');assert not output.exists()
output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
