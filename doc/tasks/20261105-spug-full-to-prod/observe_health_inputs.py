"""Observe only original registered readiness endpoints and port declarations."""
import json
from install_prod_control import remote, TASK

SCRIPT=r'''
import datetime,json,pathlib,subprocess,urllib.request
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3')
receipt=json.loads((root/'target-installation.json').read_bytes())
config=json.loads(pathlib.Path(receipt['ownerConfigurationPin']['path']).read_bytes())['targets'][receipt['targetConfigRef']]
out=[]
for service in config['services']:
 if service['role'] not in ('minio','backend','frontend'):continue
 row=json.loads(subprocess.check_output(['docker','inspect',service['id']],timeout=10))[0]
 out.append(dict(role=service['role'],id=row['Id'],ip=service['ip'],running=row['State']['Running'],
  exposedPorts=row['Config'].get('ExposedPorts'),bindings=row['HostConfig'].get('PortBindings'),
  dockerHealthcheckConfigured=bool(row['Config'].get('Healthcheck'))))
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
with opener.open('http://127.0.0.1:9000/minio/health/ready',timeout=5) as response:
 raw=response.read(65537)
 assert response.status==200 and len(raw)<=65536
 probe=dict(endpoint=response.url,status=response.status,bodyBytes=len(raw))
print(json.dumps(dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),services=out,minioProbe=probe,mutations=0)))
'''
if __name__=='__main__':
    report=remote(SCRIPT,timeout=40)
    (TASK/'main-health-inputs.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
