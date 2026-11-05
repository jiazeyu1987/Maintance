"""Install a persistent FD budget only on the idle, owned review control."""
import json
from preflight import COMMON,TASK,remote

CHECK=r'''
receipt=json.loads((root/'target-installation.json').read_bytes())
owner=read(receipt['ownerConfigurationPin']);control=read(receipt['controlConfigurationPin'])
before=business();need(before==BEFORE['business'],'BUSINESS_DRIFT')
for reference in PINS:need(pin(reference['path'])==reference,'ORIGINAL_FAILURE_CHANGED')
need(not pathlib.Path('/var/lib/spug-restore-resources/active.json').exists(),'ACTIVE_RESERVATION')
unit=receipt['service']
def idle():
 props=dict(line.split('=',1) for line in run(['systemctl','show',unit,'-p','MainPID','-p','ControlGroup']).decode().splitlines())
 pid=int(props['MainPID']);need(pid>0,'CONTROL_NOT_RUNNING')
 cg=pathlib.Path('/sys/fs/cgroup/systemd')/props['ControlGroup'].lstrip('/')/'cgroup.procs'
 if not cg.exists():cg=pathlib.Path('/sys/fs/cgroup')/props['ControlGroup'].lstrip('/')/'cgroup.procs'
 need({int(v) for v in cg.read_text().split()}=={pid},'CONTROL_WORKERS_ACTIVE')
 return pid
pid=idle()
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from recovery_resource_admission import _host_lock
fd=os.open(owner['targets'][receipt['targetConfigRef']]['replacement']['lockPath'],os.O_RDWR|os.O_NOFOLLOW)
fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
with _host_lock():
 need(not pathlib.Path('/var/lib/spug-restore-resources/active.json').exists(),'ACTIVE_RESERVATION')
 need(idle()==pid and business()==before,'PREWRITE_DRIFT')
 directory=pathlib.Path('/etc/systemd/system')/(unit+'.d');directory.mkdir(exist_ok=True)
 drop=directory/'archive-budget.conf'
 need(not drop.exists(),'BUDGET_ALREADY_CONFIGURED')
 drop_pin=append(drop,b'[Service]\nLimitNOFILE=65536\n',raw=True);drop.chmod(0o644)
 run(['systemctl','daemon-reload']);run(['systemctl','restart',unit])
 need(run(['systemctl','is-active',unit]).strip()==b'active','CONTROL_NOT_ACTIVE')
 newpid=idle()
 limit=next(line for line in pathlib.Path('/proc',str(newpid),'limits').read_text().splitlines() if line.startswith('Max open files'))
 need(limit.split()[3:5]==['65536','65536'],'LIVE_FD_LIMIT_INCORRECT')
 need(business()==before,'BUSINESS_RUNTIME_CHANGED')
 for reference in PINS:need(pin(reference['path'])==reference,'ORIGINAL_FAILURE_CHANGED')
 need(read(receipt['ownerConfigurationPin'])==owner and read(receipt['controlConfigurationPin'])==control,'CONFIGURATION_CHANGED')
 print(json.dumps({'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS','service':unit,'priorPid':pid,'currentPid':newpid,'liveLimits':limit,'dropInPin':drop_pin,'protectedFailurePinsUnchanged':len(PINS),'allBusinessIdsPidsStartTimesConfigurationUnchanged':True,'backupOrRestoreDispatched':False}))
os.close(fd)
'''
if __name__=='__main__':
    baseline=json.loads((TASK/'restore-preflight.json').read_text(encoding='utf-8'))
    failure=json.loads((TASK/'archive-budget-diagnosis.json').read_text(encoding='utf-8'))
    script=COMMON.split('receiptpath=root/')[0]+'\nBEFORE='+repr(baseline)+'\nPINS='+repr(failure['evidencePins'])+'\n'+CHECK
    out=remote('172.30.30.59',script,100)
    (TASK/'archive-budget-installed.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(out))
