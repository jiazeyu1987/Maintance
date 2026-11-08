"""Read installation phase from process/filesystem metadata; never reconcile a ledger."""
import argparse
import json
from common import TASK, remote, now, write

SCRIPT = r'''
import datetime,json,os,pathlib,subprocess
unit='spug-main-restore-'+SUFFIX+'-20261104-v3.service'
pid=subprocess.check_output(['systemctl','show',unit,'-p','MainPID']).decode().strip()
roots=[pathlib.Path('/var/lib/docker/intruoyi-data'),pathlib.Path('/mnt/intruoyi-data')]
audits=[]
for root in roots:
 if not root.is_dir():continue
 for folder in root.glob('spug-main-restore-*/configuration/installation-audit-automatic-0d44578*'):
  files=[]
  for p in folder.iterdir():
   if not p.is_file():continue
   row=dict(name=p.name,bytes=p.stat().st_size)
   if p.name.startswith('history-') and row['bytes']<16*1024**2:
    data=json.loads(p.read_bytes())
    row.update(entryCount=len(data),pinnedBytes=sum(v['pin']['bytes'] for v in data.values() if v.get('pin')))
   files.append(row)
  audits.append(dict(directory=str(folder),files=files))
rows=[]
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdecimal():continue
 try:
  comm=(p/'comm').read_text().strip()
  if 'python' not in comm:continue
  fds=[]
  for fd in (p/'fd').iterdir():
   try:
    target=os.readlink(fd)
    if 'spug-main-restore-' in target:
     fds.append(dict(fd=fd.name,name=pathlib.Path(target).name))
   except (FileNotFoundError,ProcessLookupError,PermissionError):pass
  if not fds:continue
  rows.append(dict(pid=int(p.name),comm=comm,wchan=(p/'wchan').read_text().strip(),io=(p/'io').read_text(),fds=fds))
 except (FileNotFoundError,ProcessLookupError,PermissionError):pass
print(json.dumps(dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),servicePid=pid,audits=audits,processes=rows,serverWrites=False)))
'''

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('target',choices=['58','59'])
    args=parser.parse_args()
    result=remote('172.30.30.'+args.target,'SUFFIX='+repr(args.target)+'\n'+SCRIPT,45)
    name='target-installation-observation-'+args.target+'-'+now().replace(':','-')+'.json'
    write(TASK/name,result)
    print(json.dumps(result))
