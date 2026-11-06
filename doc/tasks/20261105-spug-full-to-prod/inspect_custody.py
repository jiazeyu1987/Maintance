"""Inspect production consumers and source dependencies without business writes."""
import json
from inspect_prod import TASK, PRIVATE, HOST, remote

SCRIPT = r'''
import datetime,hashlib,json,os,pathlib,re,subprocess,urllib.request
out={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'documents':{},'queries':{},'errors':{}}
def run(args, raw=None):
 p=subprocess.run(args,input=raw,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15)
 if p.returncode:raise ValueError('READONLY_QUERY_FAILED')
 return p.stdout.decode('utf-8')
def doc(path):
 p=pathlib.Path(path);data=p.read_bytes();v=json.loads(data);out['documents'][str(p)]=v;return v
control=doc('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1/configuration/control-postboot-20261105.json')
for reference in control['sourceConfigurations'].values():
 repo=doc(reference['path'])
 for source in repo['sources'].values():
  for field in ('configurationPath','sourceIdentityPath'):
   if field in source:doc(source[field])
rows=json.loads(run(['docker','inspect',*run(['docker','ps','-aq','--no-trunc']).split()]))
names={'backend':'/intruoyi-backend','frontend':'/intruoyi-frontend','mysql':'/intruoyi-mysql','redis':'/intruoyi-redis','minio':'/ragflow_compose-minio-1'}
main={role:next(r for r in rows if r['Name']==name) for role,name in names.items()}
envs={role:dict(e.split('=',1) for e in r['Config']['Env'] if '=' in e) for role,r in main.items()}
out['roleRuntime']={r:{'id':v['Id'],'path':v['Path'],'args':v['Args'],'environmentKeys':sorted(envs[r])} for r,v in main.items()}
password=envs['mysql']['MYSQL_ROOT_PASSWORD']
shell='IFS= read -r MYSQL_PWD; export MYSQL_PWD; exec "$@"'
sql="SELECT @@server_uuid,@@GLOBAL.log_bin; SHOW DATABASES; SELECT USER,HOST,DB,COMMAND FROM information_schema.PROCESSLIST; SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA='ruoyi-vue-pro';"
out['queries']['mysql']=run(['docker','exec','-i',main['mysql']['Id'],'sh','-ec',shell,'readonly-mysql','mysql','--no-defaults','--batch','--skip-column-names','-e',sql],(password+'\n').encode())
redisargs=main['redis']['Config'].get('Cmd') or []
password=envs['redis'].get('REDIS_PASSWORD')
if '--requirepass' in redisargs:password=redisargs[redisargs.index('--requirepass')+1]
if not password:
 for document in out['documents'].values():
  ref=document.get('redis',{}).get('passwordFile')
  if ref:password=pathlib.Path(ref).read_text().strip()
if password:
 shell='IFS= read -r REDISCLI_AUTH; export REDISCLI_AUTH; exec "$@"'
 out['queries']['redisClients']=run(['docker','exec','-i',main['redis']['Id'],'sh','-ec',shell,'readonly-redis','redis-cli','--raw','CLIENT','LIST'],(password+'\n').encode())
else:
 out['queries']['redisClients']=run(['docker','exec',main['redis']['Id'],'redis-cli','--raw','CLIENT','LIST'])
 out['queries']['redisDatabases']=run(['docker','exec',main['redis']['Id'],'redis-cli','--raw','INFO','keyspace'])
addresses={'172.30.30.57','172.21.0.6','172.21.0.2','172.17.0.2','intruoyi-mysql','intruoyi-redis','ragflow_compose-minio-1'}
out['consumerReferences']=[];out['configurationScanCount']=0
for row in rows:
 if row['Id'] in {v['Id'] for v in main.values()}:continue
 text='\n'.join((row['Config'].get('Env') or [])+(row['Config'].get('Cmd') or [])+(row['Config'].get('Entrypoint') or []))
 files=[]
 for m in row['Mounts']:
  p=pathlib.Path(m['Source'])
  if m['Type']=='bind' and p.is_file() and p.stat().st_size<2*1024*1024 and p.suffix.lower() in ('.json','.yml','.yaml','.properties','.env','.conf'):
   text+='\n'+p.read_text(encoding='utf-8');files.append(str(p))
 matches=sorted(a for a in addresses if a in text)
 out['configurationScanCount']+=len(files)
 if matches:out['consumerReferences'].append(dict(id=row['Id'],name=row['Name'],running=row['State']['Running'],matches=matches,files=files))
out['connections']=run(['ss','-ntp'])
out['hostServices']=run(['systemctl','list-units','--type=service','--state=running','--no-pager','--plain'])
out['sourceService']=run(['systemctl','show','spug-intruoyi-source-57-20261105.service','-p','ActiveState','-p','MainPID','-p','LimitNOFILE'])
out['mountinfo']=pathlib.Path('/proc/self/mountinfo').read_text()
out['fstabSha256']=hashlib.sha256(pathlib.Path('/etc/fstab').read_bytes()).hexdigest()
out['capacity']={p:os.statvfs(p).f_bavail*os.statvfs(p).f_frsize for p in ('/var/lib/docker','/opt/intruoyi/runtime')}
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
for name,url in (('health','http://127.0.0.1:48081/actuator/health'),('frontend','http://127.0.0.1:8081')):
 with opener.open(url,timeout=10) as response:out[name]={'status':response.status,'body':response.read().decode() if name=='health' else ''}
print(json.dumps(out))
'''

if __name__ == '__main__':
    value=remote(HOST,SCRIPT,timeout=90)
    (PRIVATE/'custody-production.private.json').write_text(json.dumps(value),encoding='utf-8')
    report={k:value[k] for k in ('observedAt','errors','consumerReferences','configurationScanCount','sourceService','fstabSha256','capacity','health','frontend')}
    report['documentSchemas']={p:dict(schema=v.get('schemaVersion'),fields=sorted(v)) for p,v in value['documents'].items()}
    report['queries']=value['queries']
    report['roleRuntime']={r:{k:v for k,v in row.items() if k!='args'} for r,row in value['roleRuntime'].items()}
    (TASK/'production-custody.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('consumerReferences','roleRuntime','queries')}))
    print(json.dumps(dict(runningReferences=[x for x in value['consumerReferences'] if x['running']],queries=value['queries'])))
