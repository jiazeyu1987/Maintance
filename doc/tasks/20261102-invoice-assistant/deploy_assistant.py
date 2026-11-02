"""Deploy the verified existing print image and configure its same-server backend probe.
One-time task script, executed through user-authorized SSH with Python 3.
Targets and image IDs are pinned to the verified 2026-11-02 baseline.
Completed targets must not be run again. No SQL or ERP writes.
"""
import copy,hashlib,http.client,json,os,socket,subprocess,sys,time
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen
IMAGE='sha256:4314cb904db50ee7e35b5b187b7a496341265e3a6b8f09099542983e88bbd01a'
BACKEND_IMAGE='sha256:2b2160b4fba263ac7617f404fed767273ae6d21e9dbe59bfc2e2aaeb5d26c1f3'
TAG='invoice-assistant-20261102'
PROFILES={
 '172.30.30.58':('brlab-prod57-nas-test58-20261020-r3-backend','brlab-prod57-nas-test58-20261020-r3-mysql'),
 '172.30.30.57':('intruoyi-backend','intruoyi-mysql'),
 '172.30.30.59':('intruoyi-prod-nas-restore59-20261020-backend','intruoyi-prod-nas-restore59-20261020-native-mysql')}
def require(ok,message):
 if not ok:raise RuntimeError(message)
def run(args,timeout=120):
 r=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
 require(r.returncode==0,'Command failed: '+args[0]+' exit='+str(r.returncode))
 return r.stdout
def inspect(name):return json.loads(run(['docker','inspect',name]))[0]
def docker(method,path,value=None):
 c=http.client.HTTPConnection('localhost',timeout=180)
 c.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);c.sock.connect('/var/run/docker.sock')
 try:
  c.request(method,path,None if value is None else json.dumps(value),{'Content-Type':'application/json'})
  r=c.getresponse();raw=r.read();require(r.status<300,'Docker HTTP '+str(r.status))
  return json.loads(raw) if raw else None
 finally:c.close()
def private(path,value):
 fd=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w') as f:json.dump(value,f)
def clone_config(original, image, maintenance=None):
    config = copy.deepcopy(original['Config'])
    config['Image'] = image
    if maintenance is not None:
        # Environment is private, retained entirely on host. Property is explicit and overrides profile defaults.
        environment = [v for v in config['Env'] if not v.startswith('INTRUOYI_RELEASE_MAINTENANCE=')]
        environment.append('INTRUOYI_RELEASE_MAINTENANCE=' + str(maintenance).lower())
        config['Env'] = environment
    config['HostConfig'] = copy.deepcopy(original['HostConfig'])
    config['HostConfig'].pop('ContainerIDFile', None)
    endpoints = {}
    for name, entry in original['NetworkSettings']['Networks'].items():
        if name in ('host', 'none'):
            continue
        endpoint = {}
        if name != 'bridge':
            # Stopped containers may have no observed IPAddress while their
            # explicitly assigned addresses remain in IPAMConfig.
            if entry.get('IPAMConfig') is not None:
                endpoint['IPAMConfig'] = copy.deepcopy(entry['IPAMConfig'])
            elif entry.get('IPAddress'):
                endpoint['IPAMConfig'] = {'IPv4Address': entry['IPAddress']}
            if entry.get('Aliases'):
                endpoint['Aliases'] = entry['Aliases']
        endpoints[name] = endpoint
    if endpoints:
        config['NetworkingConfig'] = {'EndpointsConfig': endpoints}
    return config
def main():
 host=sys.argv[1];require(host in PROFILES,'Unregistered target')
 backend,database=PROFILES[host]
 root=Path('/mnt/intruoyi-data/invoice-assistant-deployment-20261102' if host=='172.30.30.59' else '/var/lib/docker/invoice-assistant-deployment-20261102');root.mkdir(mode=0o700,exist_ok=True)
 require(not (root/'completed.json').exists(),'Already completed; inspect receipt, do not repeat')
 before=inspect(backend);db=inspect(database)
 require(before['State']['Running'] and before['Image']==BACKEND_IMAGE,'Backend identity changed or not running')
 require(db['State']['Running'],'Database not running')
 require(not any(x=='INTRUOYI_RELEASE_MAINTENANCE=true' for x in before['Config']['Env']),'Backend is in maintenance')
 if host!='172.30.30.58':
  archive=root/'assistant-image.tar.gz';expected=(root/'assistant-image.sha256').read_text().split()[0]
  h=hashlib.sha256()
  with archive.open('rb') as f:
   for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
  require(h.hexdigest()==expected,'Image archive checksum mismatch')
  run(['docker','load','-i',str(archive)],timeout=600)
 require(json.loads(run(['docker','image','inspect',IMAGE]))[0]['Id']==IMAGE,'Print image missing')
 assistant='erp-invoice-voucher-print-assistant'
 names=run(['docker','ps','-a','--format','{{.Names}}']).decode().splitlines()
 network=next(iter(before['NetworkSettings']['Networks']))
 if host=='172.30.30.58':
  a=inspect(assistant);require(a['Image']==IMAGE and a['State']['Running'] and a['HostConfig']['NetworkMode']=='host','Existing test assistant differs')
  private(root/'assistant-before.private.json',a)
  run(['docker','stop',assistant])
  run(['docker','rename',assistant,assistant+'-before-'+TAG])
 else:
  require(assistant not in names,'Assistant already exists; inspect before replacing')
 data=Path('/opt/intruoyi/runtime/erp-invoice-voucher-print-assistant')
 for folder in ('runtime','results','uploads'):(data/folder).mkdir(parents=True,exist_ok=True,mode=0o700)
 run(['docker','create','--name',assistant,'--restart','unless-stopped','--network','bridge','-p','18733:18733',
  '-e','INVOICE_VOUCHER_PRINT_TICKET_VALIDATE_URL=http://'+backend+':48081/admin-api/system/auth/invoice-voucher-print-ticket/validate',
  '-e','INVOICE_VOUCHER_PRINT_SESSION_TTL_SECONDS=14400',
  '-v',str(data/'runtime')+':/opt/invoice-voucher-print-assistant/runtime',
  '-v',str(data/'results')+':/opt/invoice-voucher-print-assistant/浏览器运行结果',
  '-v',str(data/'uploads')+':/opt/invoice-voucher-print-assistant/服务器上传发票',IMAGE])
 run(['docker','network','connect','--alias',assistant,network,assistant])
 run(['docker','start',assistant])
 probe='fetch("http://'+assistant+':18733/",{signal:AbortSignal.timeout(8000)}).then(async r=>{if(r.status!==403||!(await r.text()).includes("没有发票凭证打印权限"))process.exit(1)}).catch(()=>process.exit(1))'
 run(['docker','run','--rm','--network',network,'--entrypoint','node',IMAGE,'-e',probe],timeout=20)
 print('Assistant image and backend network reachability verified; configuring probe only.',flush=True)
 private(root/'backend-before.private.json',before)
 config=clone_config(before,BACKEND_IMAGE)
 env=dict(x.split('=',1) for x in config['Env'])
 prop='-Dyudao.erp.invoice-voucher-print-assistant.assistant-host='
 require(prop not in env.get('JAVA_OPTS',''),'Existing explicit invoice host requires review')
 env['JAVA_OPTS']=(env.get('JAVA_OPTS','')+' '+prop+assistant).strip()
 config['Env']=[k+'='+v for k,v in env.items()]
 retained=backend+'-before-'+TAG
 require(retained not in names,'Backend recovery container already exists')
 run(['docker','stop','-t','60',backend])
 docker('POST','/containers/'+quote(before['Id'])+'/rename?name='+quote(retained))
 for network in before['NetworkSettings']['Networks']:
  if network not in ('host','none'):docker('POST','/networks/'+quote(network)+'/disconnect',{'Container':before['Id'],'Force':True})
 created=docker('POST','/containers/create?name='+quote(backend),config)
 after=inspect(created['Id'])
 require(after['Image']==before['Image'] and after['HostConfig']['PortBindings']==before['HostConfig']['PortBindings'],'Backend clone identity/ports differ')
 run(['docker','start',backend])
 address=next(iter(after['NetworkSettings']['Networks'].values()))['IPAMConfig']['IPv4Address']
 for attempt in range(180):
  try:
   with urlopen('http://'+address+':48081/actuator/health',timeout=3) as response:
    if json.load(response).get('status')=='UP':break
  except Exception:
   if attempt==179:raise
  time.sleep(2)
 else:raise RuntimeError('Backend did not become UP')
 # Verify the published helper port from the server; peer-network access was checked above.
 # Server root intentionally rejects unauthenticated callers; no fake authorized health route.
 r=subprocess.run(['curl','-s','-o',str(root/'unauthorized-entry.html'),'-w','%{http_code}','http://'+host+':18733/'],stdout=subprocess.PIPE)
 require(r.returncode==0 and r.stdout==b'403','Expected assistant unauthorized status 403')
 require('没有发票凭证打印权限' in (root/'unauthorized-entry.html').read_text(),'Unexpected helper identity')
 db_after=inspect(database)
 require(all(db_after[k]==db[k] for k in ('Id','Image')) and db_after['State']['StartedAt']==db['State']['StartedAt'],'Database changed externally')
 receipt={'host':host,'assistantImageId':IMAGE,'backendImageId':after['Image'],'backendHealth':'UP','databaseUnchanged':True,'retainedBackend':retained}
 private(root/'completed.json',receipt)
 print(json.dumps(receipt),flush=True)
if __name__=='__main__':
 try:main()
 except Exception as e:
  print('FAILED: '+type(e).__name__+': '+str(e),flush=True);sys.exit(1)
