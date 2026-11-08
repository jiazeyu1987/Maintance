"""Independent identities, semantic readiness and original MySQL state."""
import argparse,ast,json
from common import TASK,remote,write,restore_kind

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('suffix',choices=['58','59']);args=parser.parse_args();suffix=args.suffix
 tree=ast.parse((TASK.parent/'20261105-spug-prod-full-to-review/verify_restored_runtime.py').read_text(encoding='utf-8'))
 script=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SCRIPT' for t in n.targets))
 script=script.replace("root=pathlib.Path('/mnt/intruoyi-data/spug-main-restore-20261104-v3')","root=pathlib.Path(ROOT)")
 script=script.replace("'intruoyi-main-59-safe-restore-20261104-v1'","TARGET")
 script=script.replace("'http://172.30.30.59:38081/'","FRONTEND")
 script=script.replace("report['status']='PASS'",r'''
flags=subprocess.check_output(['docker','exec','-i',services['mysql']['id'],'sh','-ec',script,'restore-state-verification','mysql','--no-defaults','--protocol=SOCKET','--host=localhost','--batch','--skip-column-names','-e','SELECT @@version,@@GLOBAL.event_scheduler,@@GLOBAL.read_only,@@GLOBAL.super_read_only;'],input=secret+b'\n',timeout=10).decode().strip().split('\t')
assert flags==[BASELINE['database']['version'],BASELINE['database']['eventScheduler'],'0','0'],'DATABASE_ORIGINAL_STATE_NOT_RESTORED'
for role,row in [(role,by_id[value['id']]) for role,value in services.items()]:
 if 'Health' in row['State']:assert row['State']['Health']['Status']=='healthy','CONTAINER_HEALTH_NOT_READY'
with opener.open('http://'+services['minio']['ip']+':9000/minio/health/ready',timeout=10) as response:assert response.status==200
def checked(reference):
 raw=pathlib.Path(reference['path']).read_bytes();assert len(raw)==reference['bytes'] and hashlib.sha256(raw).hexdigest()==reference['sha256'],'CONFIGURATION_CHANGED';return json.loads(raw)
assert receipt['ownerConfigurationPin']==BASELINE['ownerConfigurationPin'] and receipt['controlConfigurationPin']==BASELINE['controlConfigurationPin']
checked(receipt['ownerConfigurationPin']);checked(receipt['controlConfigurationPin'])
report['mysqlGlobalState']=dict(version=flags[0],eventScheduler=flags[1],readOnly=flags[2],superReadOnly=flags[3],originalStateRestored=True)
report['minioReadyHTTP']=200
report['allConfiguredDockerHealthchecksHealthy']=True
report['installedConfigurationPinsUnchanged']=True
report['status']='PASS'
''')
 request=json.loads((TASK/(restore_kind(suffix)+'-ui-submission.json')).read_text(encoding='utf-8'))['request'];baseline=json.loads((TASK/('target-rollback-point-admission-'+restore_kind(suffix)+'.json')).read_text(encoding='utf-8'))
 variables=dict(ROOT=('/mnt/intruoyi-data/' if suffix=='59' else '/var/lib/docker/intruoyi-data/')+'spug-main-restore-20261104-v3',TARGET=request['targetConfigRef'],FRONTEND='http://172.30.30.'+suffix+':'+('38081' if suffix=='59' else '8081')+'/',BASELINE=baseline)
 script=script.replace('OPERATION_LITERAL',repr(request['operationId']))
 value=remote('172.30.30.'+suffix,'\n'.join(k+'='+repr(v) for k,v in variables.items())+'\n'+script,80)
 write(TASK/('restored-runtime-'+suffix+'.json'),value);print(json.dumps(value))
