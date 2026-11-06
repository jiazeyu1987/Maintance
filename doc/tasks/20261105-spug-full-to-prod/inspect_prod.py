"""Read-only production inventory; raw configuration remains private."""
import json
from pathlib import Path
import sys

TASK = Path(__file__).resolve().parent
PRIVATE = Path('C:/Spug/runtime/private/full-to-prod-20261105')
PREVIOUS = TASK.parent / '20261104-spug-selectable-restore-targets'
sys.path.insert(0, str(PREVIOUS))
from resume_readonly import SCRIPT, remote

ROOT = '/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3'
HOST = '172.30.30.57'
EXTRA = r'''
'''

if __name__ == '__main__':
    PRIVATE.mkdir(parents=True, exist_ok=True)
    value = remote(HOST, 'HOST='+repr(HOST)+'\nROOT='+repr(ROOT)+'\n'+SCRIPT, timeout=75)
    (PRIVATE/'original-production.private.json').write_text(json.dumps(value), encoding='utf-8')
    source = value['documents'].get('sourceOwner', {})
    report = {k: value[k] for k in ('host', 'observedAt', 'loadAverage', 'files', 'activeReservation', 'objectRoots')}
    report['mainContainers'] = [dict(id=r['Id'], name=r['Name'], image=r['Image'], running=r['State']['Running'],
        pid=r['State']['Pid'], startedAt=r['State']['StartedAt'], health=r['State'].get('Health',{}).get('Status'),
        ports=r['HostConfig']['PortBindings'], mounts=r['Mounts'], networkMode=r['HostConfig']['NetworkMode'],
        networks=r['NetworkSettings']['Networks']) for r in value['containers']
        if r['Name'] in ('/intruoyi-backend','/intruoyi-frontend','/intruoyi-mysql','/intruoyi-redis','/ragflow_compose-minio-1')]
    report['allContainerCount'] = len(value['containers'])
    report['sourceFields'] = sorted(source)
    (TASK/'production-inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='mainContainers'}))
    for row in report['mainContainers']:
        print(json.dumps(row))
