"""Independently check the original source after preservation FULL succeeds."""
import json
import sys

from install_prod_control import PRIVATE, TASK, remote

SCRIPT = r'''
import datetime,hashlib,json,pathlib,subprocess,urllib.request

if AFTER_CAPTURE:
 operation='smallapp-7fec29a3e132463096aec915c08acab3'
 capture=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1/capture-staging')/operation
 completion=json.loads((capture/'worker-completion.json').read_bytes())
 assert completion['schemaVersion']=='minimal-capture-worker-completion/v1' and completion['operationId']==operation
 pin=completion['data']['sourceRestorationPin'];raw=pathlib.Path(pin['path']).read_bytes()
 assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'],'SOURCE_RESTORATION_PIN_CHANGED'
 restored=json.loads(raw)
 assert restored['schemaVersion']=='minimal-capture-source-restoration/v1' and restored['restored'] is True and not restored['errors']

def run(args,raw=None):
 p=subprocess.run(args,input=raw,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=12)
 assert p.returncode==0,'SOURCE_RUNTIME_QUERY_FAILED'
 return p.stdout

rows=json.loads(run(['/usr/bin/docker','inspect',*EXPECTED]))
report=dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),services=[])
by_name={}
for row in rows:
 assert row['Id'] in EXPECTED and row['Image']==EXPECTED[row['Id']]['image'],'SOURCE_IDENTITY_CHANGED'
 assert row['Name']==EXPECTED[row['Id']]['name'],'SOURCE_NAME_CHANGED'
 assert row['State']['Running'] and not row['State']['Paused'] and not row['State']['Restarting'],'SOURCE_NOT_RUNNING'
 by_name[row['Name']]=row
 report['services'].append(dict(id=row['Id'],image=row['Image'],name=row['Name'],running=True,pid=row['State']['Pid'],startedAt=row['State']['StartedAt']))
mysql=by_name['/intruoyi-mysql']
env=dict(e.split('=',1) for e in mysql['Config']['Env'] if '=' in e)
raw=(env['MYSQL_ROOT_PASSWORD']+'\n').encode()
sql='SELECT @@server_uuid,@@GLOBAL.read_only,@@GLOBAL.super_read_only;'
values=run(['/usr/bin/docker','exec','-i',mysql['Id'],'sh','-ec','IFS= read -r MYSQL_PWD; export MYSQL_PWD; exec "$@"','preservation-readonly','mysql','--no-defaults','--batch','--skip-column-names','-e',sql],raw).decode().strip().split('\t')
assert values==['0fa6c22b-5a90-11f1-ade1-0242ac150002','0','0'],'SOURCE_DATABASE_NOT_RESTORED'
report['databaseUuid']=values[0]
report['databaseOriginalWriteFlagsRestored']=True
assert run(['/usr/bin/docker','exec',by_name['/intruoyi-redis']['Id'],'redis-cli','--raw','PING']).strip()==b'PONG','SOURCE_REDIS_NOT_READY'
report['redisPing']='PONG'
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
for name,url in [('backend','http://127.0.0.1:48081/actuator/health'),('frontend','http://127.0.0.1:8081/'),('minio','http://127.0.0.1:9000/minio/health/live')]:
 with opener.open(url,timeout=8) as response:
  assert response.status==200,'SOURCE_HTTP_NOT_READY'
  report[name+'HttpStatus']=response.status
  if name=='backend':
   assert json.load(response)['status']=='UP','SOURCE_BACKEND_NOT_UP'
   report['backendHealth']='UP'
unit='spug-intruoyi-source-57-20261105.service'
assert run(['systemctl','is-active',unit]).strip()==b'active','SOURCE_CONTROL_NOT_ACTIVE'
pid=int(run(['systemctl','show',unit,'-p','MainPID','--value']).strip())
line=next(v for v in pathlib.Path('/proc',str(pid),'limits').read_text().splitlines() if v.startswith('Max open files'))
assert line.split()[3:5]==['65536','65536'],'SOURCE_CONTROL_FD_BUDGET_CHANGED'
report['sourceControlActive']=True
report['sourceControlFdLimit']=65536
print(json.dumps(report))
'''

if __name__ == '__main__':
    after_capture='--after-capture' in sys.argv
    if not after_capture:
        point=json.loads((TASK/'preservation-full-point-verified.json').read_text(encoding='utf-8'))
        assert point['state']=='SUCCEEDED' and point['sourceStartCommandsCompleted'] is True
    baseline=json.loads((PRIVATE/'original-production.private.json').read_text(encoding='utf-8'))
    names={'/intruoyi-backend','/intruoyi-frontend','/intruoyi-mysql','/intruoyi-redis','/ragflow_compose-minio-1'}
    expected={r['Id']:dict(image=r['Image'],name=r['Name']) for r in baseline['containers'] if r['Name'] in names}
    assert len(expected)==5
    report=remote('EXPECTED='+repr(expected)+'\nAFTER_CAPTURE='+repr(after_capture)+'\n'+SCRIPT,65)
    report['backupPublicationVerified']=not after_capture
    filename='source-runtime-after-capture.json' if after_capture else 'preserved-source-runtime.json'
    (TASK/filename).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
