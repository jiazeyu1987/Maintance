"""Read the live capture stack through a bounded signal-free process observation."""
import json
from install_prod_control import remote,TASK

SCRIPT=r'''
import datetime,json,pathlib,subprocess
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1/capture-staging/smallapp-7fec29a3e132463096aec915c08acab3')
job=json.loads((root/'job-configuration.json').read_bytes())
report=dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),configurationFields=sorted(job))
report['processes']=[]
parents={29758,29761}
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdecimal():continue
 try:
  stat=(p/'stat').read_text().split();parent=int(stat[3])
  if parent in parents or int(p.name) in parents:
   cmd=(p/'cmdline').read_bytes().split(b'\0')
   programs={x.decode() for x in cmd if x in [b'mysql',b'mysqldump',b'dump',b'exec',b'/usr/bin/mysql',b'/usr/bin/mysqldump']}
   report['processes'].append(dict(pid=int(p.name),parent=parent,executable=pathlib.Path(cmd[0].decode()).name,programs=sorted(programs),state=stat[2],cpuTicks=int(stat[13])+int(stat[14]),wchan=(p/'wchan').read_text()))
 except (FileNotFoundError,ProcessLookupError,PermissionError):pass
print(json.dumps(report))
'''
if __name__=='__main__':
    value=remote(SCRIPT,35)
    (TASK/'preservation-phase.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
    print(json.dumps(value))
