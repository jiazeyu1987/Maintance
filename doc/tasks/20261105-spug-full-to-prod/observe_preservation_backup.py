"""Bounded read-only progress for the one already submitted preservation FULL."""
import json
import sys
from pathlib import Path
from install_prod_control import remote, TASK, PRIVATE

SCRIPT=r'''
import datetime,json,pathlib,time
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
operation='smallapp-7fec29a3e132463096aec915c08acab3'
repository_id='433710bb8eb93e78351878966cb06caec1c420e87ef3d5c8dff9c493dc085eb9'
report=dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),operationId=operation)
report['directories']={}
for relative in ['ledger/'+operation,'capture-staging/'+operation,'repository-operations/433710bb8eb93e78351878966cb06caec1c420e87ef3d5c8dff9c493dc085eb9']:
 p=root/relative
 if not p.is_dir():report['directories'][relative]=None;continue
 files=sorted(p.iterdir(),key=lambda f:f.stat().st_mtime,reverse=True)
 report['directories'][relative]=dict(count=len(files),latest=[dict(name=f.name,bytes=f.stat().st_size,mtime=f.stat().st_mtime,isDirectory=f.is_dir()) for f in files[:12]])
report['workers']=[]
repository=root/'repository-operations'/repository_id
start=json.loads((repository/'start.json').read_bytes())
report['nativeDeadlineSecondsRemaining']=round(start['deadlineMonotonic']-time.monotonic(),1)
report['nativeReadbackRecords']=[]
for record in repository.glob('*/readback-originals.json'):
 value=json.loads(record.read_bytes())
 report['nativeReadbackRecords'].append(dict(fileCount=len(value['archivedFilePins']),payloadBytes=sum(p['bytes'] for p in value['archivedFilePins'].values()),recordBytes=record.stat().st_size))
report['staging']={}
report['dataObservationScratch']={}
report['knownCaptureFiles']={}
p=root/'capture-staging'/operation/'payload'
report['payloadTopLevel']=[dict(name=f.name,bytes=f.stat().st_size,isDirectory=f.is_dir()) for f in p.iterdir()] if p.is_dir() else []
for name in ['database.sql.gz','011-source-data.json','012-source-data-after.json','capture-content-point.json']:
 p=root/'capture-staging'/operation/'payload'/name
 report['knownCaptureFiles'][name]=dict(bytes=p.stat().st_size,mtime=p.stat().st_mtime) if p.is_file() else None
for name in ['payload','semantic-capture']:
 p=root/'capture-staging'/operation/name
 count=total=0;latest=0
 if p.is_dir():
  for f in p.rglob('*'):
   if f.is_file():s=f.stat();count+=1;total+=s.st_size;latest=max(latest,s.st_mtime)
 report['staging'][name]=dict(files=count,bytes=total,latestMtime=latest)
for name in ['scratch-before','scratch-after']:
 p=root/'capture-staging'/operation/name
 if not p.is_dir():
  report['dataObservationScratch'][name]=None
  continue
 parts=[f for f in p.iterdir() if f.is_dir() and f.name.isdecimal()]
 latest=max(parts,key=lambda f:f.stat().st_mtime) if parts else None
 report['dataObservationScratch'][name]=dict(tableDirectoriesStarted=len(parts),highestTableIndex=max((int(f.name) for f in parts),default=None),latestDirectoryMtime=latest.stat().st_mtime if latest else None)
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdecimal():continue
 try:
  cmd=(p/'cmdline').read_bytes()
  if not (operation.encode() in cmd or repository_id.encode() in cmd) or b'python' not in cmd:continue
  report['workers'].append(dict(pid=int(p.name),io=(p/'io').read_text(),state=(p/'stat').read_text().split()[2],startTicks=(p/'stat').read_text().split()[21],role='repository' if repository_id.encode() in cmd else 'capture-or-query'))
 except (FileNotFoundError,ProcessLookupError,PermissionError):pass
print(json.dumps(report))
'''

NAS=r'''
import hashlib,os
op=root/'repository-operations'/repository_id
start=json.loads((op/'start.json').read_bytes());pin=start['configurationPin']
raw=pathlib.Path(pin['path']).read_bytes()
assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'],'SOURCE_CONFIGURATION_CHANGED'
archives=pathlib.Path(json.loads(raw)['repositoryRoot'])/'archives'
candidates=[p for p in archives.iterdir() if p.name.endswith(repository_id)]
assert len(candidates)==1,'ORIGINAL_ARCHIVE_UNRESOLVED'
count=total=0;latest=0
for directory,dirs,files in os.walk(candidates[0],followlinks=False):
 for name in files:
  p=pathlib.Path(directory,name);assert not p.is_symlink(),'ARCHIVE_SYMLINK'
  s=p.stat();count+=1;total+=s.st_size;latest=max(latest,s.st_mtime)
report['nas']=dict(archiveName=candidates[0].name,files=count,bytes=total,latestFileMtime=latest,scope='exact-original-360-archive-only')
'''

if __name__=='__main__':
    script=SCRIPT.replace('print(json.dumps(report))',NAS+'\nprint(json.dumps(report))') if '--nas' in sys.argv else SCRIPT
    value=remote(script,55)
    (PRIVATE/'preservation-progress.private.json').write_text(json.dumps(value),encoding='utf-8')
    (TASK/'preservation-progress.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
    if '--nas' in sys.argv:
        (TASK/'preservation-nas-progress.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
    if '--brief' in sys.argv:
        print(json.dumps(dict(observedAt=value['observedAt'],workers=[dict(pid=w['pid'],state=w['state'],role=w['role'],startTicks=w['startTicks']) for w in value['workers']],nativeReadbackRecords=value['nativeReadbackRecords'],nativeDeadlineSecondsRemaining=value['nativeDeadlineSecondsRemaining'],staging=value['staging'],capturePointPresent=value['knownCaptureFiles']['capture-content-point.json'] is not None,nas=value.get('nas'))))
    else:
        print(json.dumps({k:value[k] for k in ['observedAt','operationId','workers','staging','dataObservationScratch','knownCaptureFiles','payloadTopLevel']}))
