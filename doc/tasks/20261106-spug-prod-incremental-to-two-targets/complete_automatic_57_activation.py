"""Finish the exact staged installation after proving the old source override won."""
import ast
import hashlib
import json
from common import TASK, PRIVATE, SOURCE, remote, write
from install_automatic_57 import SCRIPT

COMMIT = '0d445782dc06995b3c84b1b45146ea4b75483f92'
PREFIX = SCRIPT[:SCRIPT.index("need(not pathlib.Path('/var/lib/spug-restore-resources/active.json')")]
TREE = ast.parse(SCRIPT)
RETAINED_FUNCTION = next(ast.get_source_segment(SCRIPT, n) for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name == 'verify_retained')
PROBE = next(ast.literal_eval(n.value) for n in TREE.body if isinstance(n, ast.Assign)
             and any(isinstance(t, ast.Name) and t.id == 'health_probe' for t in n.targets))
RESUME = r'''
need(not pathlib.Path('/var/lib/spug-restore-resources/active.json').exists(),'ACTIVE_RESERVATION')
root=pathlib.Path(INSTALLED[0]['control']['workingDirectory'])
staged=json.loads((root/'configuration'/('staged-automatic-'+COMMIT[:7]+'.json')).read_bytes())
need(staged['sourceCommit']==COMMIT and staged['status']=='STAGED','STAGED_IDENTITY_CHANGED')
new=staged['controllers'];policy=staged['policy']
for old,current in zip(INSTALLED,ACTUAL):
 need(active_pid(old['unit'])==current['pid'],'ACTUAL_PID_CHANGED')
 need(document(old['controlPin'])==old['control'],'ORIGINAL_CONTROL_CHANGED')
for item in new:
 need(document(item['controlConfigurationPin'])==item['control'],'NEW_CONTROL_CHANGED')
 engine=pathlib.Path(item['engine']);version=json.loads((engine/'package.json').read_bytes())
 need(version['packageSha256']==staged['fileManifestSha256'],'MANIFEST_CHANGED')
 need(all(pin(engine/name)['sha256']==sha for name,sha in version['files'].items()),'PACKAGE_CHANGED')
need(ACTUAL[0]['pid']==20349 and ACTUAL[1]['pid']==20273,'EXPLICIT_ACTIVATION_STATE_CHANGED')
need(INSTALLED[0]['args'][2]==ACTUAL[0]['args'][2] and INSTALLED[0]['args'][5]==ACTUAL[0]['args'][5],'SOURCE_NOT_PROVEN_OLD_GENERATION')
need(ACTUAL[1]['args'][2]==str(pathlib.Path(new[1]['engine'])/'control_entry.py') and json.loads(ACTUAL[1]['args'][5])==new[1]['controlConfigurationPin'],'TARGET_NOT_PROVEN_NEW_GENERATION')
lock=os.open(policy['sourceLockPath'],os.O_RDWR|os.O_NOFOLLOW);fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
for proc in pathlib.Path('/proc').iterdir():
 if not proc.name.isdecimal():continue
 try:cmd=(proc/'cmdline').read_bytes()
 except (FileNotFoundError,ProcessLookupError):continue
 if any(item['control']['workingDirectory'].encode() in cmd for item in new):need(b'control_entry.py' in cmd,'ACTIVE_WORKER')
sys.path.insert(0,str(pathlib.Path(new[0]['engine'])/'common'))
from recovery_backup_epoch import read_current
epoch=read_current(policy);event=document(epoch['eventPin'])
need(epoch==staged['epoch'] and event['kind']=='INITIALIZED' and event['operationId'] is None,'EPOCH_CHANGED')
before=snapshot();fstab=pin('/etc/fstab');beforemounts=mounts();verify_retained()
health=json.loads(run([new[1]['control']['pythonPin']['path'],'-B','-c',HEALTH_PROBE,canonical(new[1]['controlConfigurationPin']).decode(),SOURCE,TARGET],timeout=50,env=dict(os.environ,**new[1]['control']['environment'])))
source=new[0];directory=pathlib.Path('/etc/systemd/system')/(source['service']+'.d')
names=[p.name for p in directory.glob('*.conf')]
leading=max([len(name)-len(name.lstrip('z')) for name in names]+[0])+1
dropin=directory/('z'*leading+'-automatic-'+COMMIT[:7]+'.conf')
need(all(dropin.name>name for name in names),'OVERRIDE_ORDER_INVALID')
control=source['control'];engine=pathlib.Path(source['engine'])
command=control['pythonPin']['path']+' -B '+str(engine/'control_entry.py')+' serve --config-pin '+"'"+canonical(source['controlConfigurationPin']).decode()+"'"
write_new(dropin,('[Service]\nEnvironment=PYTHONPATH='+control['environment']['PYTHONPATH']+'\nExecStart=\nExecStart='+command+'\n').encode());dropin.chmod(0o644)
run(['systemctl','daemon-reload']);run(['systemctl','restart',source['service']])
need(run(['systemctl','is-active',source['service']]).strip()==b'active','SOURCE_NOT_ACTIVE')
for item in new:
 pid=active_pid(item['service']);args=(pathlib.Path('/proc')/str(pid)/'cmdline').read_bytes().decode().split('\0')
 need(args[2]==str(pathlib.Path(item['engine'])/'control_entry.py') and json.loads(args[5])==item['controlConfigurationPin'],'LIVE_GENERATION_INVALID')
 limits=(pathlib.Path('/proc')/str(pid)/'limits').read_text();need(any(l.startswith('Max open files') and l.split()[3:5]==['65536','65536'] for l in limits.splitlines()),'LIVE_FD_LIMIT_INVALID')
 item['pid']=pid
item=new[1];need(item['pid']==ACTUAL[1]['pid'],'TARGET_RESTARTED_AGAIN')
new[0].update(initialPreviousPid=new[0]['previousPid'],previousPid=ACTUAL[0]['pid'],dropinPin=pin(dropin))
new[1]['dropinPin']=pin(pathlib.Path('/etc/systemd/system')/(new[1]['service']+'.d')/('zzzz-automatic-'+COMMIT[:7]+'.conf'))
for item in new:
 for attempt in range(21):
  try:http(item['control'],'/selections',90);break
  except urllib.error.URLError as error:
   if not isinstance(error.reason,ConnectionRefusedError) or attempt==20:raise
   time.sleep(1)
 item['selectionsHttp']=200
plan=http(new[0]['control'],'/incremental-plan?sourceConfigRef='+SOURCE)
need(plan['state']=='BASELINE_REQUIRED' and plan['reasonCode']=='BACKUP_POINT_EPOCH_REQUIRED','ACTUAL_PLAN_INVALID')
need(snapshot()==before and len(before)==198,'ORIGINAL_DOCKER_RUNTIME_CHANGED')
verify_retained();need(pin('/etc/fstab')==fstab and mounts()==beforemounts,'PROTECTED_STORAGE_CHANGED')
result=dict(staged,status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),controllers=new,plan=plan,targetSemanticHealth=health,allOriginalContainersUnchanged=True,fstabAndProtectedMountsUnchanged=True,retainedFailureFilesPreserved=len(RETAINED_PINS),backupPerformed=False,restorePerformed=False,activationOverrideOrderCorrected=True)
write_new(root/'configuration'/('installation-automatic-'+COMMIT[:7]+'.json'),canonical(result))
print(json.dumps(result))
'''

if __name__ == '__main__':
    installed = json.loads((PRIVATE / 'automatic-57-installed.private.json').read_text(encoding='utf-8'))
    actual = json.loads((PRIVATE / 'automatic-57-actual-activation.private.json').read_text(encoding='utf-8'))
    retained = json.loads((TASK / 'registered-binlog-tool-restored.json').read_text(encoding='utf-8'))['failedOriginalPins']
    for number in ('365', '366'):
        retained += json.loads((PRIVATE / ('failed-' + number + '-all-pins.private.json')).read_text(encoding='utf-8'))['pins']
    assert len(retained) == len({p['path'] for p in retained}) == 10044
    output = PRIVATE / 'automatic-control-installation-57.private.json'
    assert not output.exists()
    values = dict(INSTALLED=installed, ACTUAL=actual, COMMIT=COMMIT, SOURCE=SOURCE,
                  TARGET='intruoyi-main-57-safe-restore-20261105-v2', RETAINED_PINS=retained, HEALTH_PROBE=PROBE)
    code = '\n'.join(k + '=' + repr(v) for k, v in values.items()) + '\n' + PREFIX + '\n' + RETAINED_FUNCTION + '\n' + RESUME
    compile(code, '<finish-staged-activation>', 'exec')
    result = remote('172.30.30.57', code, 300)
    write(output, result)
    public = dict(result, controllers=[{k: v for k, v in item.items() if k != 'control'} for item in result['controllers']])
    write(TASK / 'automatic-control-installation-57.json', public)
    print(json.dumps({k: v for k, v in public.items() if k != 'controllers'}))
