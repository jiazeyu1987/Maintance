"""Read-only diagnosis of the original containers' post-start network identity."""
import json
from resume_readonly import TASK,remote

SCRIPT=r'''
import datetime,json,pathlib,subprocess,sys
root=pathlib.Path('/mnt/intruoyi-data/spug-main-restore-20261104-v3')
receipt=json.loads((root/'target-installation.json').read_bytes())
owner=json.loads(pathlib.Path(receipt['ownerConfigurationPin']['path']).read_bytes())
control=json.loads(pathlib.Path(receipt['controlConfigurationPin']['path']).read_bytes())
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from recovery_main_target import network_attachments,network_configuration
target=owner['targets'][receipt['targetConfigRef']]
diffs=[];networks=[]
for service in target['services']:
 row=json.loads(subprocess.check_output(['docker','inspect',service['id']],timeout=15))[0]
 old=target['mainApplication']['networkAttachments'][service['role']];now=network_attachments(row)
 if old!=now:diffs.append({'role':service['role'],'expected':old,'actual':now,
   'ipam':{n:x.get('IPAMConfig') for n,x in row['NetworkSettings']['Networks'].items()}})
for expected in target['mainApplication']['networks']:
 query=subprocess.run(['docker','network','inspect',expected['id']],capture_output=True,timeout=15)
 actual=json.loads(subprocess.check_output(['docker','network','inspect',expected['name']],timeout=15))[0]
 networks.append({'expected':expected,'expectedIdExists':query.returncode==0,
   'actual':network_configuration(actual,sorted(actual['Containers']))})
print(json.dumps({'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'diffs':diffs,'networks':networks,'remoteMutation':False}))
'''
if __name__=='__main__':
 result=remote('172.30.30.59',SCRIPT)
 (TASK/'review-started-network-diagnosis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False))
