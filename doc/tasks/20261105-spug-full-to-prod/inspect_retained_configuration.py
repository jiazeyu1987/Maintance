"""Read-only comparison of original normalized operation and current owner."""
import json
from install_prod_control import TASK,ROOT,TARGET,APP,remote

SCRIPT=r'''
import datetime,hashlib,json,pathlib
root=pathlib.Path(ROOT)
receipt=json.loads((root/'target-installation.json').read_bytes())
owner=json.loads(pathlib.Path(receipt['ownerConfigurationPin']['path']).read_bytes())
original=json.loads((root/'recovery-operations'/OPERATION/'configuration.json').read_bytes())
def changes(a,b,path=''):
 if type(a)!=type(b):return [path+':type']
 if isinstance(a,dict):
  out=[]
  for key in sorted(set(a)|set(b)):
   p=path+'/'+key
   if key not in a or key not in b:out.append(p+':presence')
   else:out+=changes(a[key],b[key],p)
  return out
 if a!=b:return [path]
 return []
print(json.dumps(dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 sourceCommit=receipt['sourceCommit'],sourceKeysEqual=set(original['sources'])==set(owner['sources']),
 targetKeysEqual=set(original['targets'])==set(owner['targets']),
 exactSelectedTarget=original['targets'][TARGET]==owner['targets'][TARGET],
 exactSelectedSource=original['sources'][APP]==owner['sources'][APP],
 differences=changes(original,owner))))
'''

if __name__=='__main__':
    failure=json.loads((TASK/'database-state-failure-diagnosis.json').read_text(encoding='utf-8'))
    variables=dict(ROOT=ROOT,TARGET=TARGET,APP=APP,OPERATION=failure['operationId'])
    report=remote('\n'.join(k+'='+repr(v) for k,v in variables.items())+'\n'+SCRIPT)
    (TASK/'retained-configuration-comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
