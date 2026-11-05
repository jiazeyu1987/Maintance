"""Read the five original source services; never alter source configuration/data."""
import json
from preflight import TASK, remote

SCRIPT = r'''
import datetime,json,subprocess,urllib.request
baseline=BASELINE_LITERAL
expected={row['id']:row for row in baseline['containers']}
rows=json.loads(subprocess.check_output(['docker','inspect',*expected],timeout=15))
assert {row['Id'] for row in rows}==set(expected),'SOURCE_CONTAINER_SET_CHANGED'
services=[]
for row in rows:
 old=expected[row['Id']]
 assert old['observation']=='LIVE_INSPECT_OK'
 assert row['Image']==old['image'],'SOURCE_IMAGE_CHANGED'
 assert row['State']['Running'] is True and not row['State']['Restarting']
 assert row['State']['Pid']==old['state']['Pid'],'SOURCE_PID_CHANGED'
 assert row['State']['StartedAt']==old['state']['StartedAt'],'SOURCE_RESTARTED'
 services.append(dict(role=old['role'],id=row['Id'],image=row['Image'],running=True,pid=row['State']['Pid'],startedAt=row['State']['StartedAt']))
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open('http://127.0.0.1:48081/actuator/health',timeout=5) as response:
 assert response.status==200
 health=json.load(response)['status']
assert health=='UP'
with opener.open('http://127.0.0.1:8081/',timeout=5) as response:frontend=response.status
assert frontend==200
print(json.dumps(dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS',host='172.30.30.57',originalFiveContainersImagesPidsAndStartTimesPreserved=True,backendHealth=health,frontendHTTP=frontend,services=services)))
'''

if __name__ == '__main__':
    baseline=json.loads((TASK/'source-runtime-before.json').read_text(encoding='utf-8'))
    report=remote('172.30.30.57',SCRIPT.replace('BASELINE_LITERAL',repr(baseline)),timeout=30)
    (TASK/'source-preservation-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({key:value for key,value in report.items() if key!='services'}))
