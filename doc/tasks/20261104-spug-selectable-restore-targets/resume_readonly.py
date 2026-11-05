"""Current installed control/consumer inventory; raw configuration stays private."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import sys

TASK = Path(__file__).resolve().parent
PRIVATE = Path('C:/Spug/runtime/private/restore-targets-20261104')
sys.path.insert(0, str(TASK.parent / '20261104-spug-prod-full-to-test'))
from repair_preflight import remote

SCRIPT = r'''
import datetime,hashlib,json,pathlib,subprocess
root=pathlib.Path(ROOT)
out={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'host':HOST,
 'loadAverage':pathlib.Path('/proc/loadavg').read_text().split()[:3],'documents':{},'files':{}}
def file(p):
 p=pathlib.Path(p)
 if not p.is_file():return
 raw=p.read_bytes();out['files'][str(p)]={'path':str(p),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
 return raw
def doc(p,key):
 raw=file(p)
 if raw is not None:out['documents'][key]=json.loads(raw)
doc(root/'installation.json','componentInstallation')
doc(root/'target-installation.json','targetInstallation')
receipt=out['documents'].get('targetInstallation')
if receipt:
 doc(receipt['ownerConfigurationPin']['path'],'owner')
 doc(receipt['controlConfigurationPin']['path'],'control')
 service=receipt['service']
 out['service']={'name':service,'properties':subprocess.check_output(['systemctl','show',service,'--property=ActiveState,SubState,UnitFileState,MainPID,ExecMainStartTimestamp,FragmentPath'],timeout=10).decode()}
 out['service']['unit']=subprocess.check_output(['systemctl','cat',service],timeout=10).decode()
 file(pathlib.Path('/etc/systemd/system')/service)
 engine=pathlib.Path(out['documents']['owner']['formalModuleDirectory']).parent
 package=json.loads((engine/'package.json').read_bytes());out['package']=package
 out['packageFilesMatch']=all((engine/name).is_file() and hashlib.sha256((engine/name).read_bytes()).hexdigest()==sha for name,sha in package['files'].items())
 out['operations']={name:[str(p.relative_to(root/name)) for p in (root/name).rglob('operation.json')] for name in ('ledger','operations','recovery-operations') if (root/name).exists()}
 out['claims']=[str(p.relative_to(root)) for p in root.rglob('*claim*') if p.is_file()]
else:
 out['configurationFiles']=[str(p) for p in (root/'configuration').glob('*')]
 doc('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1/configuration/control-postboot-20261105.json','sourceControl')
 doc('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1/configuration/recovery.json','sourceOwner')
ids=subprocess.check_output(['docker','ps','--all','--no-trunc','--format','{{.ID}}'],timeout=15).decode().split()
out['containers']=json.loads(subprocess.check_output(['docker','inspect',*ids],timeout=20))
out['activeReservation']=pathlib.Path('/var/lib/spug-restore-resources/active.json').exists()
if out['activeReservation']:doc('/var/lib/spug-restore-resources/active.json','activeReservation')
out['objectRoots']={}
for row in out['containers']:
 if not row['State']['Running'] or 'minio' not in (row['Name']+' '+row['Config']['Image']).lower():continue
 for m in row['Mounts']:
  if m['Destination']!='/data':continue
  p=pathlib.Path(m['Source']);out['objectRoots'][row['Id']]={'root':str(p),'buckets':sorted(x.name for x in p.iterdir() if x.is_dir() and not x.name.startswith('.'))}
  iam=p/'.minio.sys/config/iam'
  out['objectRoots'][row['Id']]['identityPaths']=[str(x.relative_to(iam)) for section in ('users','service-accounts') for x in (iam/section).glob('*/identity.json')]
print(json.dumps(out))
'''

def observe(suffix):
    root=('/mnt/intruoyi-data/' if suffix=='59' else '/var/lib/docker/intruoyi-data/')+'spug-main-restore-20261104-v3'
    host='172.30.30.'+suffix
    value=remote(host, 'HOST='+repr(host)+'\nROOT='+repr(root)+'\n'+SCRIPT, timeout=100)
    (PRIVATE/('resume-'+suffix+'.private.json')).write_text(json.dumps(value),encoding='utf-8')
    owner=value['documents'].get('owner',{})
    report={k:value[k] for k in ('host','observedAt','loadAverage','files','activeReservation','objectRoots')}
    report.update({'controlService':value.get('service',{}).get('properties'),
      'ownerLimits':owner.get('dataLimits'),'sqlExpandedLimit':owner.get('maxExpandedBytes'),
      'formalModuleDirectory':owner.get('formalModuleDirectory'),'packageFilesMatch':value.get('packageFilesMatch'),
      'packageFileCount':len(value.get('package',{}).get('files',{})),
      'operations':value.get('operations'),'claims':value.get('claims'),
      'containers':[{'id':r['Id'],'name':r['Name'],'image':r['Image'],'configuredImage':r['Config']['Image'],
        'running':r['State']['Running'],'pid':r['State']['Pid'],'startedAt':r['State']['StartedAt'],
        'health':r['State'].get('Health',{}).get('Status'),'publishedPorts':r['HostConfig']['PortBindings'],
        'mounts':[{'source':m['Source'],'target':m['Destination'],'type':m['Type'],'rw':m['RW']} for m in r['Mounts']]}
        for r in value['containers']]})
    (TASK/('resume-'+suffix+'-readonly.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report

if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for result in pool.map(observe,('57','59')):
            print(json.dumps({k:result[k] for k in ('host','observedAt','loadAverage','controlService','ownerLimits','sqlExpandedLimit','formalModuleDirectory','packageFilesMatch','packageFileCount','activeReservation','operations','claims','objectRoots')},ensure_ascii=False))
