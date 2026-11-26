"""Read-only production runtime restart policy verification."""
import json,subprocess,sys
from datetime import datetime
from pathlib import Path
base=Path('C:/SpugHandoff/release')
task=Path(__file__).resolve().parent
sys.path.insert(0,str(base/'source/ops/spug/release-center'))
from intruoyi_runtime import Runtime,ssh_source_bytes
config=json.loads((base/'executor.private.json').read_text(encoding='utf-8-sig'))
r=Runtime(config); profile=r.profile('prod')
assert profile['host']=='172.30.30.57'
remote=r'''
import json,subprocess,urllib.request
from pathlib import Path

def run(args):
    result=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=25)
    if result.returncode: raise RuntimeError('Read-only probe failed: '+args[0])
    return result.stdout

containers={}
for role in ('backend','frontend'):
    item=json.loads(run(['docker','inspect',profile[role]]))[0]
    health=item.get('Config',{}).get('Healthcheck') or {}
    command=' '.join(health.get('Test') or [])
    state=item['State']
    containers[role]=dict(name=item['Name'],containerId=item['Id'],image=item['Config']['Image'],restartPolicy=item['HostConfig'].get('RestartPolicy'),restartCount=item['RestartCount'],running=state['Running'],restarting=state['Restarting'],oomKilled=state['OOMKilled'],exitCode=state['ExitCode'],startedAt=state['StartedAt'],health=(state.get('Health') or {}).get('Status'),healthcheck=dict(configured=bool(health),interval=health.get('Interval'),timeout=health.get('Timeout'),retries=health.get('Retries'),usesActuatorHealth='/actuator/health' in command))
unit_files=run(['systemctl','list-unit-files','--no-pager','--no-legend','intruoyi-service-recovery*']).decode('utf-8').strip()
units=run(['systemctl','list-units','--all','--no-pager','--no-legend','intruoyi-service-recovery*']).decode('utf-8').strip()
properties=run(['systemctl','show','intruoyi-service-recovery@prod.service','--property=LoadState,ActiveState,SubState,UnitFileState,MainPID,FragmentPath']).decode('utf-8').strip()
processes=run(['ps','-eo','pid=,args=']).decode('utf-8')
recovery_pids=[]
for line in processes.splitlines():
    parts=line.strip().split(None,1)
    if len(parts)==2 and 'service_recovery.py' in parts[1]: recovery_pids.append(int(parts[0]))
configdir=Path('/etc/intruoyi-service-recovery')
recovery=dict(unitFiles=unit_files,units=units,productionUnit=properties,matchingProcessPids=recovery_pids,configurationDirectoryExists=configdir.exists(),configurationNames=sorted(x.name for x in configdir.iterdir()) if configdir.is_dir() else [],installedEntryExists=Path('/opt/intruoyi-maintenance/ops/spug/release-center/service_recovery.py').is_file())
backend_http=None
try:
    with urllib.request.urlopen('http://127.0.0.1:48081/actuator/health',timeout=8) as response:
        body=json.load(response); backend_http=dict(httpStatus=response.status,status=body.get('status'))
except Exception as error:
    backend_http=dict(errorType=type(error).__name__)
docker=run(['systemctl','show','docker.service','--property=LoadState,ActiveState,SubState,UnitFileState,Restart']).decode('utf-8').strip()
print(json.dumps(dict(environment='prod',host=profile['host'],containers=containers,serviceRecovery=recovery,backendHealth=backend_http,dockerService=docker)))
'''
code='profile='+repr({k:profile[k] for k in ('host','backend','frontend')})+'\n'+remote
result=subprocess.run(['ssh',*r.ssh_options(),'root@'+profile['host'],profile['python']+' -'],input=ssh_source_bytes(code),capture_output=True,timeout=100)
if result.returncode:
    private=base/'private/prod-backend-auto-restart-check-20261126'
    private.mkdir(exist_ok=True)
    (private/'probe.stderr.private.txt').write_bytes(result.stderr)
    (private/'probe.stdout.private.txt').write_bytes(result.stdout)
    print(json.dumps(dict(status='FAILED',exitCode=result.returncode,errorTypes=[line for line in result.stderr.decode('utf-8',errors='replace').splitlines() if line.startswith(('RuntimeError:','FileNotFoundError:','SyntaxError:','KeyError:'))])))
    raise SystemExit(1)
report=json.loads(result.stdout)
report['checkedAt']=datetime.now().astimezone().isoformat(timespec='seconds')
(task/'runtime-readonly-evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
