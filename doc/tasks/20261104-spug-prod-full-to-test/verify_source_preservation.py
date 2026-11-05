"""Compare protected source containers with the approved pre-repair baseline."""
import json
from repair_preflight import remote, TASK

SCRIPT=r'''
import datetime,json,pathlib,subprocess
before=json.loads(pathlib.Path('/root/spug-postboot-repair-20261105/docker-management-repair/applications.before.private.json').read_bytes())
capture=json.loads(pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1/configuration/capture.json').read_bytes())
minio=capture['source']['minioContainerId']
now={c['Id']:c for c in json.loads(subprocess.check_output(['docker','inspect']+[c['Id'] for c in before],timeout=15))}
report={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'containers':[]}
for old in before:
 current=now[old['Id']]
 assert current['State']['Running'] and not current['State']['Restarting'] and not current['State']['Paused']
 assert current['Image']==old['Image'] and current['Config']==old['Config'] and current['HostConfig']==old['HostConfig'] and sorted(current['Mounts'],key=lambda x:x['Destination'])==sorted(old['Mounts'],key=lambda x:x['Destination'])
 stable=all(current['State'][k]==old['State'][k] for k in ('Pid','StartedAt'))
 if current['Id']!=minio:assert stable,'UNRELATED_SERVICE_RESTARTED'
 report['containers'].append({'id':current['Id'],'name':current['Name'],'configurationPreserved':True,'pidAndStartedAtUnchanged':stable,'sourceMinioCaptureLifecycle':current['Id']==minio})
report['unchangedPidAndStartedAtCount']=sum(c['pidAndStartedAtUnchanged'] for c in report['containers'])
report['status']='PASS'
print(json.dumps(report))
'''
if __name__=='__main__':
    report=remote('172.30.30.57',SCRIPT,timeout=35)
    (TASK/'source-after-full-preservation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report))
