"""Independently verify the exact registered MAIN instance after real restore.

No configuration, credential, business row, or database mutation is emitted.
"""
import json
from preflight import remote, TASK

SCRIPT = r'''
import datetime,hashlib,json,pathlib,subprocess,urllib.request
root=pathlib.Path('/mnt/intruoyi-data/spug-main-restore-20261104-v3')
operation=OPERATION_LITERAL
receipt=json.loads((root/'target-installation.json').read_bytes())
owner=json.loads(pathlib.Path(receipt['ownerConfigurationPin']['path']).read_bytes())
target=owner['targets'][receipt['targetConfigRef']]
assert receipt['targetConfigRef']=='intruoyi-main-59-safe-restore-20261104-v1'
services={s['role']:s for s in target['services']}
rows=json.loads(subprocess.check_output(['docker','inspect']+[s['id'] for s in target['services']],timeout=15))
by_id={r['Id']:r for r in rows}
report={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'operationId':operation,'targetConfigRef':receipt['targetConfigRef'],'services':[]}
for role,expected in services.items():
 row=by_id[expected['id']]
 assert row['Image']==expected['imageId'] and row['State']['Running'] is True
 assert not row['State']['Paused'] and not row['State']['Restarting']
 report['services'].append(dict(role=role,id=row['Id'],image=row['Image'],running=True,pid=row['State']['Pid'],startedAt=row['State']['StartedAt'],health=row['State'].get('Health',{}).get('Status')))
report['backendHealth']=json.loads(subprocess.check_output(['docker','exec',services['backend']['id'],'curl','-fsS','--max-time','5','http://127.0.0.1:48081/actuator/health'],timeout=8))['status']
assert report['backendHealth']=='UP'
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open('http://172.30.30.59:38081/',timeout=5) as response:report['frontendHTTP']=response.status
assert report['frontendHTTP']==200
secret_pin=target['secrets']['mysql']['MYSQL_ROOT_PASSWORD']
secret=pathlib.Path(secret_pin['path']).read_bytes()
assert len(secret)==secret_pin['bytes'] and hashlib.sha256(secret).hexdigest()==secret_pin['sha256']
assert secret and not any(c in secret for c in (b'\n',b'\r',b'\0'))
script='test -z "${MYSQL_TEST_LOGIN_FILE:-}"; test -n "${HOME:-}"; test ! -e "$HOME/.mylogin.cnf"; test ! -L "$HOME/.mylogin.cnf"; IFS= read -r MYSQL_PWD; export MYSQL_PWD; exec "$@"'
report['databaseUuid']=subprocess.check_output(['docker','exec','-i',services['mysql']['id'],'sh','-ec',script,'restore-verification','mysql','--no-defaults','--protocol=SOCKET','--host=localhost','--batch','--skip-column-names','-e','SELECT @@server_uuid;'],input=secret+b'\n',timeout=8).decode().strip()
assert report['databaseUuid']==target['replacement']['databaseUuid']
replacement=json.loads((pathlib.Path(target['replacement']['stateRoot'])/operation/'replacement-result.json').read_bytes())
assert replacement['state']=='SUCCEEDED' and replacement['operationId']==operation and replacement['targetConfigRef']==receipt['targetConfigRef']
report['replacementState']=replacement['state']
report['status']='PASS'
print(json.dumps(report))
'''

if __name__ == '__main__':
    operation=json.loads((TASK/'restore-ui-submission.json').read_text(encoding='utf-8'))['request']['operationId']
    report=remote('172.30.30.59',SCRIPT.replace('OPERATION_LITERAL',repr(operation)),timeout=40)
    (TASK/'restored-runtime.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report))
