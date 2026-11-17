import sys,json
from pathlib import Path
sys.path.insert(0,'C:/Spug/runtime/private/spug-backup59-mvp-20261116')
import collect59
collect59.PY='/mnt/intruoyi-data/recovery-tools/python/bin/python3.12'
apply=sys.argv[1:]==['--apply']
assert apply or not sys.argv[1:]
code=r'''
import json,pathlib,subprocess,hashlib,sys,os,importlib.util
root=pathlib.Path('/mnt/intruoyi-data/recovery-preparation/8eb768e9953a04f7f2143fe333d93e865368379456f927b668ae741e2df6c207')
op='smallapp-b638d7c9b2324703aee90ec1a6c1008d'
target='spug-empty59-8eb768e9953a'
result=json.loads((root/'recovery-operations'/op/'result.json').read_bytes())
assert result['state']=='SUCCEEDED' and result['actualExitCode']==0
cfg=json.loads(pathlib.Path('/mnt/intruoyi-data/recovery-tools/prepare-target.private.json').read_bytes())
policy=cfg['points']['smallapp-8978e87efa3c47bebd6b0e0bc825f7b7']['fileStorage']
assert policy==[{'id':28,'bucket':'yudao','sourceEndpoints':['http://host.docker.internal:9000']}]
spec=importlib.util.spec_from_file_location('native','/mnt/intruoyi-data/recovery-tools/prepare_target_native.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
sys.path.insert(0,'/mnt/intruoyi-data/recovery-tools/engine/common')
from recovery_prepared_storage import connection_update
def run(args,input=None):
 p=subprocess.run(args,input=input,capture_output=True,timeout=90)
 assert p.returncode==0,'COMMAND_FAILED_'+args[0]+'_'+str(p.returncode)
 return p.stdout
mysql=['docker','exec','-i',target+'-mysql','mysql','--defaults-extra-file=/run/recovery/mysql-client.cnf','--batch','--skip-column-names']
def query(sql):return run(mysql,sql.encode('utf-8')).decode('utf-8')
with m.NativePreparation(cfg).host_lock():
 assert not (pathlib.Path(cfg['hostReservationRoot'])/'active.json').exists(),'RESTORE_ACTIVE'
 containers={r:json.loads(run(['docker','inspect',target+'-'+r]))[0] for r in ['backend','frontend','mysql','minio']}
 for role,c in containers.items():
  assert c['Name']=='/'+target+'-'+role and c['State']['Running']
  assert target in c['NetworkSettings']['Networks'],'WRONG_TARGET_NETWORK'
 cols={line.split('\t')[0] for line in query('DESCRIBE `ruoyi-vue-pro`.infra_file_config;').splitlines()}
 assert {'id','config','deleted'} <= cols
 raw=bytes.fromhex(query("SELECT HEX(config) FROM `ruoyi-vue-pro`.infra_file_config WHERE id=28 AND deleted=b'0';").strip())
 before=json.loads(raw)
 endpoint='http://'+containers['minio']['NetworkSettings']['Networks'][target]['IPAddress']+':9000'
 access=run(['docker','exec',target+'-minio','cat','/run/recovery/minio-root-user']).decode().strip()
 secret=run(['docker','exec',target+'-minio','cat','/run/recovery/minio-root-password']).decode().strip()
 observed={'id':28,'bucket':before['bucket'],'endpoint':before['endpoint'],'sha256':hashlib.sha256(raw).hexdigest()}
 statement,receipt=connection_update('ruoyi-vue-pro',policy[0],observed,endpoint,access,secret)
 receipt.update(operationId=op,target=target,applied=APPLY)
 if APPLY:
  evidence=root/'post-restore-storage-repair'
  evidence.mkdir(mode=0o700)
  fd=os.open(evidence/'before.private.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
  with os.fdopen(fd,'wb') as f:f.write(raw)
  for role in ['frontend','backend']:run(['docker','stop',containers[role]['Id']])
  for role in ['frontend','backend']:
   assert not json.loads(run(['docker','inspect',containers[role]['Id']]))[0]['State']['Running']
  rows=query(statement+'\nSELECT ROW_COUNT();').strip()
  assert rows=='1','STORAGE_UPDATE_ROW_COUNT'
  after=json.loads(bytes.fromhex(query("SELECT HEX(config) FROM `ruoyi-vue-pro`.infra_file_config WHERE id=28;").strip()))
  expected=dict(before,endpoint=endpoint,accessKey=access,accessSecret=secret)
  assert after==expected,'STORAGE_READBACK_MISMATCH'
  for role in ['backend','frontend']:run(['docker','start',containers[role]['Id']])
  receipt['state']='APPLIED_AND_RESTARTED'
  (evidence/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
 print(json.dumps(receipt))
'''.replace('APPLY',repr(apply))
result=collect59.remote(code)
(Path(__file__).parent/('storage-repair-applied.private.json' if apply else 'storage-repair-plan.private.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
