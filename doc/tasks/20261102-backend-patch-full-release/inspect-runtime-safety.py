"""Read locks, storage, writers and recovery references; never echo secrets."""
from pathlib import Path
import concurrent.futures,json,re,subprocess,sys,time
root=Path('C:/SpugHandoff/release')
source=root/'source/ops/spug/release-center';sys.path.insert(0,str(source))
from intruoyi_runtime import Runtime,ssh_source_bytes
config=json.loads((root/'executor.private.json').read_text('utf-8'));runtime=Runtime(config)
remote_source=(source/'intruoyi_remote.py').read_text('utf-8').split("if __name__ == '__main__':")[0]
inspection=r'''
from pathlib import Path
import os
p=PROFILE
result={'storage':{},'operations':[]}
docker_root=run(['docker','info','--format','{{.DockerRootDir}}']).decode().strip()
result['dockerRoot']=docker_root
for name in dict.fromkeys(['/',p['stagingRoot'],'/var/lib/docker','/mnt/intruoyi-data',docker_root]):
    path=Path(name)
    if path.exists():
        s=os.statvfs(path);result['storage'][name]=dict(freeGiB=round(s.f_bavail*s.f_frsize/1024**3,2),totalGiB=round(s.f_blocks*s.f_frsize/1024**3,2),device=os.stat(path).st_dev)
for path in (Path(p['stagingRoot'])/'.operations').glob('OP-*.json'):
    value=json.loads(path.read_text('utf-8'))
    if value['status']=='running':
        proc=Path('/proc')/str(value['pid'])/'stat'
        raw=proc.read_text() if proc.exists() else ''
        start=raw[raw.rfind(')')+2:].split()[19] if raw else None
        result['operations'].append(dict(operationId=value['operationId'],jobId=value['jobId'],status=value['status'],workerAlive=start==value['processStart']))
lock=Path(p['stagingRoot'])/'runtime-operation.lock'
result['publicLockHeld']=False
if lock.exists():
    inode=str(lock.stat().st_ino)
    result['publicLockHeld']=any(line.split()[5].split(':')[-1]==inode for line in Path('/proc/locks').read_text().splitlines() if len(line.split())>5)
backend=inspect(p['backend']);database=inspect(p['database'])
env=dict(item.split('=',1) for item in backend['Config'].get('Env',[]))
result['datasourceAuthorities']={key:re.findall(r'jdbc:mysql://([^/?;]+)',value) for key,value in env.items() if re.search(r'jdbc:mysql://',value)}
result['backendEnvNames']=sorted(env)
result['backendMounts']=[dict(type=m['Type'],source=m['Source'],destination=m['Destination'],rw=m['RW']) for m in backend['Mounts']]
result['backendNetworks']={name:dict(ip=v.get('IPAddress'),aliases=v.get('Aliases')) for name,v in backend['NetworkSettings']['Networks'].items()}
result['backendCommandHasJdbc']=bool(re.search('jdbc:mysql',json.dumps(backend['Config'].get('Cmd'))))
result['datasourceAuthorities']['startupArguments']=re.findall(r'jdbc:mysql://([^/?;\s]+)',json.dumps(backend['Config'].get('Cmd')))
result['configLocations']=re.findall(r'--spring\.config\.[a-z-]+=([^\s";]+)',json.dumps(backend['Config'].get('Cmd'))+' '+env.get('ARGS','')+' '+env.get('INTRUOYI_EXTRA_ARGS',''))
result['mountedJdbcAuthorities']={}
for m in backend['Mounts']:
    if m['Destination'].endswith(('.properties','.yml','.yaml')):
        data=Path(m['Source']).read_text('utf-8')
        result['mountedJdbcAuthorities'][m['Destination']]=re.findall(r'jdbc:mysql://([^/?;\s]+)',data)
result['databaseNetworks']={name:dict(ip=v.get('IPAddress'),aliases=v.get('Aliases')) for name,v in database['NetworkSettings']['Networks'].items()}
result['runningContainers']=run(['docker','ps','--format','{{.Names}}']).decode().splitlines()
result['writers']=p.get('writers');result['writerInventoryConfirmed']=p.get('writerInventoryConfirmed')
result['readOnly']=sql(p,'SELECT @@global.read_only,@@global.super_read_only;')
result['replicaActive']=bool(sql(p,'SHOW REPLICA STATUS;'))
result['connectedClientHosts']=sql(p,'SELECT HOST,COUNT(*) FROM information_schema.PROCESSLIST WHERE DB=DATABASE() GROUP BY HOST ORDER BY HOST;').splitlines()
base=Path(p['stagingRoot'])/'2026-11-01-13-08-35'
result['currentReleaseFiles']=sorted(str(v.relative_to(base)) for v in base.rglob('*') if v.is_file() and (v.name=='manifest.json' or re.search(r'receipt|operation|recovery|checkpoint|deployment|release\.env',v.name)))
print(json.dumps(result))
'''
def read(env):
    profile=runtime.profile(env)
    code=remote_source+'\nPROFILE='+repr(profile)+'\n'+inspection
    result=subprocess.run(['ssh',*runtime.ssh_options(),'root@'+profile['host'],profile['python']+' -'],
                          input=ssh_source_bytes(code),capture_output=True,timeout=90)
    if result.returncode:return env,dict(status='failed',exitCode=result.returncode)
    return env,dict(status='passed',**json.loads(result.stdout))
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:result=dict(pool.map(read,('test','prod','backup')))
suffix='-'+sys.argv[1] if len(sys.argv)>1 else ''
assert not suffix or re.fullmatch('-[a-z0-9-]+',suffix)
output=Path(__file__).with_name('runtime-safety'+suffix+'.json');assert not output.exists(),'Preserve earlier safety evidence'
output.write_text(json.dumps(dict(collectedAt=time.strftime('%Y-%m-%dT%H:%M:%S'),targets=result),indent=2)+'\n',encoding='utf-8')
print(json.dumps({env:dict(status=v['status'],storage=v.get('storage'),publicLockHeld=v.get('publicLockHeld'),pendingRemote=len(v.get('operations',[])),readOnly=v.get('readOnly'),backendEnvNames=v.get('backendEnvNames'),backendMounts=v.get('backendMounts'),backendNetworks=v.get('backendNetworks')) for env,v in result.items()}))
