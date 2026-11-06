"""Read-only endpoint and writer evidence; credentials never enter the public report."""
import json
from inspect_prod import TASK,PRIVATE,HOST,remote

SCRIPT=r'''
import datetime,hashlib,json,pathlib,re,subprocess,urllib.parse
def run(args,raw=None):
 p=subprocess.run(args,input=raw,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20)
 if p.returncode:raise ValueError('READONLY_WRITER_QUERY_FAILED')
 return p.stdout.decode('utf-8')
rows=json.loads(run(['docker','inspect',*run(['docker','ps','-aq','--no-trunc']).split()]))
main={r:next(v for v in rows if v['Name']==n) for r,n in {'backend':'/intruoyi-backend','mysql':'/intruoyi-mysql','redis':'/intruoyi-redis','minio':'/ragflow_compose-minio-1'}.items()}
env={r:dict(e.split('=',1) for e in v['Config']['Env'] if '=' in e) for r,v in main.items()}
out={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'referencedEndpoints':[]}
for row in rows:
 if not row['State']['Running']:continue
 text='\n'.join((row['Config'].get('Env') or [])+(row['Config'].get('Cmd') or [])+(row['Config'].get('Entrypoint') or []))
 for m in row['Mounts']:
  p=pathlib.Path(m['Source'])
  if m['Type']=='bind' and p.is_file() and p.stat().st_size<2097152 and p.suffix.lower() in ('.json','.yml','.yaml','.properties','.env','.conf'):
   text+='\n'+p.read_text(encoding='utf-8')
 endpoints=sorted(set(re.findall(r'(?:172\.30\.30\.57|172\.21\.0\.(?:2|6)|172\.17\.0\.2|intruoyi-(?:mysql|redis)|ragflow_compose-minio-1)(?::[0-9]{1,5})?',text)))
 if endpoints:out['referencedEndpoints'].append(dict(id=row['Id'],name=row['Name'],endpoints=endpoints))
password=env['mysql']['MYSQL_ROOT_PASSWORD']
def query(sql):
 return run(['docker','exec','-i',main['mysql']['Id'],'sh','-ec','IFS= read -r MYSQL_PWD; export MYSQL_PWD; exec "$@"','writer-custody','mysql','--no-defaults','--batch','--skip-column-names','-e',sql],(password+'\n').encode())
out['fileConfigurationDescribe']=query('DESCRIBE `ruoyi-vue-pro`.`infra_file_config`;')
fields={line.split('\t')[0] for line in out['fileConfigurationDescribe'].splitlines()}
if not {'id','config','storage','deleted'}<=fields:raise ValueError('FILE_CONFIG_SCHEMA_UNEXPECTED')
configs=query('SELECT id,storage,config FROM `ruoyi-vue-pro`.`infra_file_config` WHERE deleted=0;')
out['fileConfigurationsPrivate']=configs
iamroot=pathlib.Path('/opt/intruoyi/runtime/data/minio/.minio.sys/config/iam')
iam={str(p.relative_to(iamroot)):json.loads(p.read_text(encoding='utf-8')) for p in iamroot.rglob('*.json') if p.is_file() and p.stat().st_size<2097152}
out['iamPrivate']=iam
out['iamSummary']=[dict(path=k,fields=sorted(v)) for k,v in iam.items()]
out['redisRequirepassEmpty']=run(['docker','exec',main['redis']['Id'],'redis-cli','--raw','CONFIG','GET','requirepass']).splitlines()==['requirepass','']
out['redisAclPrivate']=run(['docker','exec',main['redis']['Id'],'redis-cli','--raw','ACL','LIST'])
out['toolTree']={};out['mountPaths']=[]
for role,row in main.items():
 for m in row['Mounts']:
  p=pathlib.Path(m['Source'])
  item=dict(role=role,source=str(p),exists=p.exists(),isSymlink=p.is_symlink(),resolved=str(p.resolve()))
  if p.exists():item.update(mode=p.stat().st_mode,device=p.stat().st_dev,inode=p.stat().st_ino)
  out['mountPaths'].append(item)
for m in main['backend']['Mounts']:
 if m['RW']:continue
 p=pathlib.Path(m['Source'])
 if p.is_dir():
  items=list(p.rglob('*'));out['toolTree'][str(p)]=dict(files=sum(x.is_file() for x in items),directories=sum(x.is_dir() for x in items),symlinks=[str(x.relative_to(p)) for x in items if x.is_symlink()],bytes=sum(x.stat().st_size for x in items if x.is_file()))
sourcepid=int(run(['systemctl','show','spug-intruoyi-source-57-20261105.service','-p','MainPID','--value']).strip())
out['sourceLimits']=[l for l in pathlib.Path('/proc/%s/limits'%sourcepid).read_text().splitlines() if l.startswith('Max open files')]
out['sourceOpenFiles']=len(list(pathlib.Path('/proc/%s/fd'%sourcepid).iterdir()))
out['dataSizes']={r:run(['du','-sb','/opt/intruoyi/runtime/data/'+r]).split()[0] for r in ('mysql','minio','redis')}
out['configurationFields']=[]
for line in configs.splitlines():
 configid,storage,body=line.split('\t',2);value=json.loads(body)
 item=dict(id=configid,storage=storage,fields=sorted(value))
 for key in ('endpoint','bucket','domain'):
  if key in value:item[key]=value[key]
 out['configurationFields'].append(item)
out['iamIdentityPins']={}
for section in ('users','service-accounts'):
 for p in (iamroot/section).glob('*/identity.json'):
  files=[p] if p.is_file() else sorted(x for x in p.rglob('*') if x.is_file())
  out['iamIdentityPins'][str(p.relative_to(iamroot))]={str(f.relative_to(iamroot)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
out['iamPolicyPins']={str(p.relative_to(iamroot)):hashlib.sha256(p.read_bytes()).hexdigest() for section in ('policies','policydb') for p in (iamroot/section).rglob('*') if p.is_file()}
out['runningHostReferences']=[]
for row in rows:
 if not row['State']['Running'] or row['Id'] in {x['Id'] for x in main.values()}:continue
 for key,value in dict(e.split('=',1) for e in row['Config']['Env'] if '=' in e).items():
  if '172.30.30.57' not in value:continue
  urls=[]
  for url in re.findall(r'https?://[^\s,;]+',value):
   parsed=urllib.parse.urlsplit(url)
   if parsed.hostname=='172.30.30.57':urls.append(dict(scheme=parsed.scheme,host=parsed.hostname,port=parsed.port or (443 if parsed.scheme=='https' else 80)))
  out['runningHostReferences'].append(dict(id=row['Id'],name=row['Name'],environmentKey=key,urls=urls))
out['programAvailability']={name:run(['sh','-c','command -v '+name+' || true']).strip() for name in ('mc','iptables','ip6tables','ip')}
installation=json.loads(pathlib.Path('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3/installation.json').read_text())
out['installation']=installation
print(json.dumps(out))
'''
if __name__=='__main__':
    result=remote(HOST,SCRIPT,timeout=120)
    (PRIVATE/'writer-ownership.private.json').write_text(json.dumps(result),encoding='utf-8')
    report={k:v for k,v in result.items() if not k.endswith('Private')}
    (TASK/'writer-ownership.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
