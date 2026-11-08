import json
from common import TASK,remote,write
SCRIPT=r'''
import hashlib,json,pathlib,subprocess
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
documents={}
for name in ['configuration/control-postboot-20261105.json','configuration/repository.json','configuration/capture.json','configuration/source-identity.json','configuration/source-postboot-installation.json']:
 p=root/name;value=json.loads(p.read_bytes());documents[name]=value
out={}
def walk(value,path=''):
 if isinstance(value,dict):
  for key,item in value.items():
   if any(s in key.lower() for s in ('password','credential','headers','secret','token')):continue
   walk(item,path+'/'+key)
 elif isinstance(value,list):
  for i,item in enumerate(value):walk(item,path+'/'+str(i))
 elif isinstance(value,str) and any(s in value for s in ('/engine','PYTHON','/configuration/','/bin/','/capture','/binder')):out[path]=value
for name,value in documents.items():walk(value,name)
out['serviceText']=subprocess.check_output(['systemctl','cat','spug-intruoyi-source-57-20261105.service']).decode()
print(json.dumps(out))
'''
if __name__=='__main__':
 value=remote('172.30.30.57',SCRIPT)
 write(TASK/'source-program-paths.json',value);print(json.dumps(value))
