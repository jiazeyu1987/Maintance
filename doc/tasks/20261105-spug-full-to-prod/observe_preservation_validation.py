"""Observe only the existing preservation worker without signals or payload reads."""
import json
from install_prod_control import remote, TASK

SCRIPT = r'''
import datetime,json,pathlib,os
pid=29314;p=pathlib.Path('/proc')/str(pid)
report=dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),workerPid=pid,workerPresent=p.is_dir())
if p.is_dir():
 stat=(p/'stat').read_text().split()
 assert stat[21]=='7940506','ORIGINAL_WORKER_IDENTITY_CHANGED'
 assert b'433710bb8eb93e78351878966cb06caec1c420e87ef3d5c8dff9c493dc085eb9' in (p/'cmdline').read_bytes(),'ORIGINAL_WORKER_COMMAND_CHANGED'
 counts={k:int(v) for k,v in (line.split(':',1) for line in (p/'io').read_text().splitlines())}
 archive='/var/lib/docker/intruoyi-data/prod57-spug-rehearsal-20261021/nas/Backup/BackupPackage/spug-intruoyi57-remediation-20261024/safe/57/archives/prod-standard-433710bb8eb93e78351878966cb06caec1c420e87ef3d5c8dff9c493dc085eb9/'
 opened=[]
 for f in (p/'fd').iterdir():
  try:
   name=os.readlink(f)
   if name.startswith(archive):
    info=dict(line.split(':',1) for line in (p/'fdinfo'/f.name).read_text().splitlines())
    opened.append(dict(category='SQL' if 'database.sql' in name else 'ARCHIVED_CONTENT',position=int(info['pos'])))
  except FileNotFoundError:
   # The live worker can close an FD between listing it and reading fdinfo.
   opened.append(dict(category='FD_CLOSED_DURING_OBSERVATION'))
 report.update(processStartTicks=stat[21],state=stat[2],ioCounters=counts,openArchiveFiles=opened)
print(json.dumps(report))
'''

if __name__ == '__main__':
    value=remote(SCRIPT,35)
    path=TASK/'native-preservation-final-verification-progress.json'
    previous=json.loads(path.read_text(encoding='utf-8')) if path.exists() else None
    if previous and value['workerPresent'] and 'ioCounters' in previous:
        value['rcharIncreaseSincePrevious']=value['ioCounters']['rchar']-previous['ioCounters']['rchar']
    path.write_text(json.dumps(value,indent=2),encoding='utf-8')
    print(json.dumps(value))
