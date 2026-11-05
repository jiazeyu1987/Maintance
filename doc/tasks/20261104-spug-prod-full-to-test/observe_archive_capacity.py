"""Read pinned historical manifests and service budgets; never submit operations."""
import json
from repair_preflight import remote, TASK, PRIVATE

SCRIPT=r'''
import json,pathlib,subprocess,hashlib
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
def read(pin):
 p=pathlib.Path(pin['path']);b=p.read_bytes()
 assert len(b)==pin['bytes'] and hashlib.sha256(b).hexdigest()==pin['sha256']
 return json.loads(b)
out={'services':{},'points':[]}
for service in ['spug-intruoyi-source-57-20261105.service']:
 out['services'][service]=subprocess.check_output(['systemctl','show',service,'-p','LimitNOFILE','-p','LimitNOFILESoft','-p','MainPID'],timeout=5).decode()
out['inotifyMaxWatches']=int(pathlib.Path('/proc/sys/fs/inotify/max_user_watches').read_text())
for p in (root/'registry/points').glob('*.json'):
 point=read(json.loads(p.read_bytes()));result=read(point['resultPin'])
 manifest=read(result['data']['manifestPin'])
 files={pathlib.Path(v['path']) for v in manifest['payloadRefs']}
 paths=set(files)
 for f in files:paths.update(f.parents)
 row={'reference':point['reference'],'state':result.get('state'),'manifestPin':result['data']['manifestPin'],'payloadFiles':len(files),'payloadBytes':sum(v['bytes'] for v in manifest['payloadRefs']),'fileAndAncestorPaths':len(paths),'requiredWithReserve':len(paths)+128,'databasePayloads':[{'name':pathlib.Path(v['path']).name,'bytes':v['bytes']} for v in manifest['payloadRefs'] if 'database.sql' in pathlib.Path(v['path']).name]}
 out['points'].append(row)
out['engineBudgetCode']=[]
for p in (root/'engine').rglob('*.py'):
 lines=p.read_text(encoding='utf-8').splitlines()
 hits=[(i,l) for i,l in enumerate(lines) if any(t in l for t in ['ArchivePathGuard','RLIMIT_NOFILE','setrlimit','LimitNOFILE'])]
 for i,l in hits:out['engineBudgetCode'].append({'file':str(p.relative_to(root)),'line':i+1,'code':'\n'.join(lines[max(0,i-2):i+3])})
print(json.dumps(out))
'''
if __name__=='__main__':
 raw=remote('172.30.30.57',SCRIPT)
 (PRIVATE/'archive-capacity-pins.private.json').write_text(json.dumps(raw),encoding='utf-8')
 raw['target']=remote('172.30.30.58',"import json,pathlib,subprocess; print(json.dumps({'budget':subprocess.check_output(['systemctl','show','spug-main-restore-58-20261104-v3.service','-p','LimitNOFILE','-p','LimitNOFILESoft','-p','MainPID']).decode(),'inotifyMaxWatches':int(pathlib.Path('/proc/sys/fs/inotify/max_user_watches').read_text())}))")
 (TASK/'archive-capacity.json').write_text(json.dumps(raw,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(raw))
