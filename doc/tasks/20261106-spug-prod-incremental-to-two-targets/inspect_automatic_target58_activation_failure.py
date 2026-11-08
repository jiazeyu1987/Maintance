"""Observe failed resume without querying any control API or changing history."""
import json
from common import TASK,PRIVATE,remote,write
from inspect_failed_automatic_target58 import SCRIPT

EXTRA=r'''
audit=root/'configuration'/'installation-audit-automatic-0d44578-resume-1'
audit_files=[]
for p in sorted(audit.iterdir()):
 item=dict(pin=pin(p))
 if p.name.startswith(('history-','strict-history-')):
  data=json.loads(p.read_bytes());files=[r for r in data.values() if r.get('kind')=='file']
  item.update(entries=len(data),files=len(files),totalPinnedBytes=sum(r['pin']['bytes'] for r in files),
   largestFiles=sorted([r['pin'] for r in files],key=lambda r:r['bytes'],reverse=True)[:8])
 elif p.name=='source-idle-query-audit.json':item['document']=json.loads(p.read_bytes())
 audit_files.append(item)
out['auditFiles']=audit_files
out['serviceProperties']=command(['systemctl','show',unit,'-p','MainPID','-p','ActiveState','-p','SubState','-p','ExecMainStartTimestamp']).decode()
owned_sockets=set()
for p in (pathlib.Path('/proc')/str(pid)/'fd').iterdir():
 try:target_name=str(p.readlink())
 except FileNotFoundError:continue
 if target_name.startswith('socket:['):owned_sockets.add(target_name[8:-1])
listeners=[]
for name in ('tcp','tcp6'):
 for line in (pathlib.Path('/proc')/str(pid)/'net'/name).read_text().splitlines()[1:]:
  row=line.split()
  if row[3]=='0A' and int(row[1].split(':')[1],16)==control['listenPort']:
   listeners.append(dict(port=control['listenPort'],inode=row[9],ownedByControlPid=row[9] in owned_sockets))
out['controlListeners']=listeners
for name in ('constructor-preactivation-automatic-0d44578-resume-1','constructor-postactivation-automatic-0d44578-resume-1'):
 p=root/'configuration'/name/'constructor-verification.json'
 out[name]=dict(exists=p.exists(),pin=pin(p) if p.exists() else None)
out['journalTail']=command(['journalctl','-u',unit,'--since','2026-11-07 18:43:00','--no-pager','-o','short-iso','-n','60']).decode()
print(json.dumps(out))
'''

if __name__=='__main__':
    candidate=json.loads((PRIVATE/'automatic-target-candidate-58-0d44578.private.json').read_text(encoding='utf-8'))
    code='C='+repr(candidate)+'\nSOURCE='+repr('intruoyi-57-safe-20261024-v1')+'\nSINCE=1794074400\n'+SCRIPT.replace('print(json.dumps(out))',EXTRA)
    value=remote('172.30.30.58',code,timeout=120)
    write(PRIVATE/'automatic-target58-resume-activation-failure.private.json',value)
    old=json.loads((PRIVATE/'automatic-target-closure-58.private.json').read_text(encoding='utf-8'))
    states=('Running','Paused','Restarting','Pid','StartedAt','FinishedAt')
    selected=('observedAt','host','unit','pid','controlPin','ownerPin','oldPackage','stagedPackage','stage','newDropins','retainedOriginalCount','allRetainedOriginalPinsMatch','activeReservationExists','controlListeners','serviceProperties','constructor-preactivation-automatic-0d44578-resume-1','constructor-postactivation-automatic-0d44578-resume-1')
    public={key:value[key] for key in selected}
    public['rolesComparedWith173744Utc']={role:dict(sameId=row['Id']==old['services'][role]['Id'],sameImage=row['Image']==old['services'][role]['Image'],
        sameMounts=sorted(row['Mounts'],key=lambda x:x['Destination'])==sorted(old['services'][role]['Mounts'],key=lambda x:x['Destination']),
        sameState=all(row['State'][k]==old['services'][role]['State'][k] for k in states),status=row['State']['Status']) for role,row in value['roles'].items()}
    public['auditFiles']=[{k:v for k,v in row.items() if k!='document'} for row in value['auditFiles']]
    public['noControlApiCalled']=True
    public['serverWrites']=False
    write(TASK/'automatic-target58-resume-activation-failure.json',public)
    print(json.dumps(public,ensure_ascii=False))
