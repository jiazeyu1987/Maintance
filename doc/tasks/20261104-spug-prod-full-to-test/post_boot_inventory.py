"""Read-only boot, container ownership and listener inventory; raw configs private."""
import concurrent.futures
import datetime
import json
import subprocess
from observe_current_state import PRIVATE, PROFILES, TASK

REMOTE = r'''
import collections,datetime,json,pathlib,subprocess
def run(args,timeout=12):
 result=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
 if result.returncode:raise RuntimeError('COMMAND_EXIT_'+str(result.returncode))
 return result.stdout.decode('utf-8','replace')
out={'host':HOST,'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'bootId':pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'uptimeSeconds':pathlib.Path('/proc/uptime').read_text().split()[0],
 'memory':{},'blockedProcesses':[],'containers':[],'errors':{}}
for line in pathlib.Path('/proc/meminfo').read_text().splitlines():
 key,value=line.split(':',1)
 if key in ('MemTotal','MemAvailable','SwapTotal','SwapFree'):out['memory'][key]=value.strip()
for process in pathlib.Path('/proc').iterdir():
 if not process.name.isdigit():continue
 try:
  status=(process/'status').read_text()
  if '\nState:\tD' in '\n'+status:out['blockedProcesses'].append({'pid':int(process.name),'wait':(process/'wchan').read_text().strip()})
 except OSError:pass
try:
 listing=[json.loads(line) for line in run(['docker','ps','-a','--format','{{json .}}']).splitlines() if line]
 out['allContainerSummaries']=listing
 out['containerCount']=len(listing)
 out['runningContainerSummaries']=[{k:row.get(k) for k in ('ID','Names','Image','State','Status','Ports')} for row in listing if row.get('State')=='running']
 selected=[row['ID'] for row in listing if row.get('State') in ('running','restarting','paused') or ':48081->' in row.get('Ports','') or row.get('Names') in ('intruoyi-backend','intruoyi-frontend','brlab-prod57-nas-test58-20261020-r3-mysql','brlab-prod57-nas-test58-20261020-r3-redis','brlab-prod57-nas-test58-20261020-r3-minio','brlab-prod57-nas-test58-20261020-r3-backend')]
 if len(selected)>70:raise RuntimeError('RUNNING_CONTAINER_BOUND_EXCEEDED')
 out['containers']=json.loads(run(['docker','inspect']+selected,20)) if selected else []
except Exception as error:out['errors']['containerInventory']=type(error).__name__
try:out['listeners']=run(['ss','-lntp'])
except Exception as error:out['errors']['listeners']=type(error).__name__
try:out['controlUnits']=run(['systemctl','list-units','--all','--no-pager','--no-legend','*spug*','*backup*restore*'])
except Exception as error:out['errors']['controlUnits']=type(error).__name__
print(json.dumps(out))
'''

def observe(profile):
    host = profile['host']
    args = ['C:/Windows/System32/OpenSSH/ssh.exe', '-F', 'NUL', '-o', 'BatchMode=yes', '-o',
            'StrictHostKeyChecking=yes', '-o', 'IdentitiesOnly=yes', '-i',
            'C:/SpugHandoff/release/private/sshIdentityFile', '-o',
            'UserKnownHostsFile=C:/SpugHandoff/release/private/sshKnownHostsFile', '-o',
            'ConnectTimeout=10', 'root@' + host, profile['python'] + ' -B -']
    result = subprocess.run(args, input=('HOST='+repr(host)+'\n'+REMOTE).encode('utf-8'), capture_output=True, timeout=45)
    if result.returncode:
        (PRIVATE / (host+'-post-boot-error.private.txt')).write_bytes(result.stderr + result.stdout)
        raise RuntimeError('POST_BOOT_OBSERVATION_FAILED_'+host)
    raw = json.loads(result.stdout)
    (PRIVATE / (host+'-post-boot.private.json')).write_text(json.dumps(raw), encoding='utf-8')
    report = {key:value for key,value in raw.items() if key not in ('containers','allContainerSummaries')}
    report['containers'] = []
    for container in raw['containers']:
        labels=container.get('Config',{}).get('Labels') or {}
        report['containers'].append({'id':container['Id'],'name':container['Name'],'image':container['Image'],
          'state':{k:container['State'].get(k) for k in ('Status','Running','Restarting','Error','ExitCode','StartedAt','FinishedAt')},
          'health':container['State'].get('Health',{}).get('Status'),
          'ports':container.get('HostConfig',{}).get('PortBindings'),
          'restartPolicy':container.get('HostConfig',{}).get('RestartPolicy'),
          'compose':{k:labels.get('com.docker.compose.'+k) for k in ('project','service','project.working_dir','project.config_files')},
          'mounts':[{k:m.get(k) for k in ('Type','Source','Destination','RW')} for m in container.get('Mounts',[])]})
    (TASK / (host+'-post-boot.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    concise={key:value for key,value in report.items() if key not in ('containers','listeners')}
    concise['listeners']=[line for line in report.get('listeners','').splitlines() if any(s in line for s in (':48081 ',':8081 ',':32657 ',':34657 ',':43658 '))]
    concise['containers']=[{k:c[k] for k in ('name','state','ports','compose')} for c in report['containers'] if any(s in c['name'] for s in ('backend','frontend','redis','mysql','minio'))]
    return concise

if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for report in pool.map(observe,[p for p in PROFILES if p['host'] in ('172.30.30.57','172.30.30.58')]):
            print(json.dumps(report,ensure_ascii=False))
