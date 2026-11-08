"""Independently verify the established local control routes after both restores."""
import argparse,ast,hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
from common import TASK,PRIVATE,SOURCE,remote,now,write
from closeout_contracts import automatic_chain,current_installations,file_pin,controller_generation

SCRIPT=r'''
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
Import-Module ($PSHOME+'/Modules/Microsoft.PowerShell.Utility/Microsoft.PowerShell.Utility.psd1') -ErrorAction Stop
$transportRoot='C:/Spug/runtime/private/restore-targets-20261104'
$stable=$transportRoot+'/restore_control_transport.ps1'
if((Get-FileHash -LiteralPath $stable -Algorithm SHA256).Hash -ne 'TRANSPORT_SHA_LITERAL' -or (Get-Item -LiteralPath $stable).Length -ne TRANSPORT_BYTES_LITERAL){throw 'INSTALLED_TRANSPORT_PIN_CHANGED'}
$rows=@()
foreach($suffix in @('58','59')){
 $receipt=Get-Content -LiteralPath ($transportRoot+'/transport-'+$suffix+'.json') -Encoding utf8 | ConvertFrom-Json
 $port=if($suffix -eq '58'){43658}else{33659}
 if($receipt.target -ne ('172.30.30.'+$suffix) -or [int]$receipt.controlPort -ne $port){throw 'TARGET_TRANSPORT_RECEIPT_CHANGED'}
 $task=Get-ScheduledTask -TaskName ('SpugMainRestoreTransport'+$suffix+'-20261104')
 if($task.State -ne 'Running' -or $task.Actions.Count -ne 1 -or $task.Principal.RunLevel -ne 'Limited'){throw 'TARGET_TRANSPORT_TASK_CHANGED'}
 $expected='-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File '+$stable+' -Target '+$suffix
 if($task.Actions[0].Execute -ne 'C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe' -or $task.Actions[0].Arguments -ne $expected){throw 'TARGET_TRANSPORT_STABLE_ACTION_CHANGED'}
 $parent=Get-CimInstance Win32_Process -Filter ('ProcessId='+$receipt.supervisorPid)
 $child=Get-CimInstance Win32_Process -Filter ('ProcessId='+$receipt.sshPid)
 if(-not $parent -or -not $child -or $child.ParentProcessId -ne $parent.ProcessId){throw 'TARGET_TRANSPORT_PROCESS_CHANGED'}
 if(-not $parent.CommandLine.Contains('restore_control_transport.ps1') -or -not $parent.CommandLine.Contains('-Target '+$suffix)){throw 'TARGET_TRANSPORT_SUPERVISOR_CHANGED'}
 if($child.ExecutablePath -ne 'C:\Windows\System32\OpenSSH\ssh.exe' -or -not $child.CommandLine.Contains('root@172.30.30.'+$suffix) -or -not $child.CommandLine.Contains('127.0.0.1:'+$port+':127.0.0.1:'+$port) -or -not $child.CommandLine.Contains('127.0.0.1:34657:127.0.0.1:42657')){throw 'TARGET_TRANSPORT_FORWARD_CHANGED'}
 $listeners=@(Get-NetTCPConnection -State Listen -LocalPort $port)
 if($listeners.Count -ne 1 -or $listeners[0].OwningProcess -ne $child.ProcessId -or $listeners[0].LocalAddress -ne '127.0.0.1'){throw 'TARGET_TRANSPORT_LISTENER_CHANGED'}
 $rows+=@{host=$receipt.target;controlPort=$port;sshPid=$child.ProcessId;supervisorPid=$parent.ProcessId;stableTaskRunning=$true;exactForwardingVerified=$true}
}
$rows | ConvertTo-Json -Compress
'''
CURRENT_SCRIPT = r'''
import datetime,hashlib,json,os,pathlib,stat,subprocess,sys,urllib.request

def checked(pin):
 p=pathlib.Path(pin['path']);assert p.resolve()==p and not p.is_symlink(),'CURRENT_PIN_ALIAS'
 raw=p.read_bytes();assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'],'CURRENT_PIN_CHANGED'
 return json.loads(raw)

def run(args,env=None):
 r=subprocess.run(args,capture_output=True,env=env,timeout=60)
 if r.returncode:
  sys.stderr.write(json.dumps(dict(schemaVersion='CurrentControlReadCommandFailure/v1',exitCode=r.returncode,stdout=r.stdout.decode('utf-8',errors='replace'),stderr=r.stderr.decode('utf-8',errors='replace')))+'\n')
  raise AssertionError('CURRENT_READ_COMMAND_FAILED')
 return r.stdout

def http(control,route):
 ref=control['authCredentialRef'];assert set(ref)=={'path','uid','gid','mode'}
 credential_path=pathlib.Path(ref['path']);metadata=credential_path.lstat()
 assert credential_path.resolve()==credential_path and stat.S_ISREG(metadata.st_mode) and metadata.st_nlink==1
 assert metadata.st_uid==ref['uid']==0 and metadata.st_gid==ref['gid']==0 and stat.S_IMODE(metadata.st_mode)==ref['mode']==0o600
 assert metadata.st_size<=2048
 headers=json.loads(credential_path.read_bytes())['headers']
 url='http://127.0.0.1:'+str(control['listenPort'])+route
 with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(urllib.request.Request(url,headers=headers),timeout=45) as response:
  assert response.status==200;return json.load(response)

rows=[]
for row in CONTROLLERS:
 control=checked(row['controlConfigurationPin']);checked(row['ownerConfigurationPin'])
 dropin=pathlib.Path(row['dropinPin']['path']).read_bytes()
 assert len(dropin)==row['dropinPin']['bytes'] and hashlib.sha256(dropin).hexdigest()==row['dropinPin']['sha256']
 pid_property=run(['systemctl','show',row['service'],'-p','MainPID']).decode().strip()
 assert pid_property.startswith('MainPID=') and pid_property[8:].isdecimal(),'CURRENT_CONTROL_PID_PROPERTY_INVALID'
 pid=int(pid_property[8:])
 assert pid==row['pid'],'CURRENT_CONTROL_PID_CHANGED'
 argv=pathlib.Path('/proc',str(pid),'cmdline').read_bytes().rstrip(b'\0').split(b'\0')
 assert (row['engine']+'/control_entry.py').encode() in argv,'CURRENT_CONTROL_GENERATION_CHANGED'
 assert json.loads(argv[-1])==row['controlConfigurationPin'],'CURRENT_CONTROL_CONFIG_ARG_CHANGED'
 manifest=json.loads(pathlib.Path(row['engine'],'package.json').read_bytes())
 assert manifest['packageSha256']==row['fileManifestSha256'] and manifest['variant']=='standard'
 assert hashlib.sha256(json.dumps(manifest['files'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()==row['fileManifestSha256']
 assert len(manifest['files'])==row['fileCount'] and all(hashlib.sha256(pathlib.Path(row['engine'],name).read_bytes()).hexdigest()==sha for name,sha in manifest['files'].items())
 if row.get('currentReceiptPin'):checked(row['currentReceiptPin'])
 if row.get('targetConfigRef'):
  target_ref=row['targetConfigRef'];owner=checked(row['ownerConfigurationPin'])
  selected=http(control,'/selections?targetConfigRef='+target_ref)
  assert target_ref in next(item for item in selected['applications'] if item['sourceConfigRef']==SOURCE)['freshTargetConfigRefs']
  health=json.loads(run([control['pythonPin']['path'],'-B','-c',HEALTH_PROBE,json.dumps(row['controlConfigurationPin']),SOURCE,target_ref,json.dumps(row.get('epochPolicy'))],env=dict(os.environ,**control['environment'])))
  assert all(value['result']['ready'] and value['result']['httpStatus']==200 for value in health.values())
  if row.get('epochPolicy') is not None:
   sys.path.insert(0,str(pathlib.Path(row['engine'])/'common'))
   from recovery_backup_epoch import read_current
   epoch=read_current(row['epochPolicy']);assert epoch==row['epoch'] and epoch['state']=='READY'
  else:epoch=None
  actual=dict(targetConfigRef=target_ref,selectionsHttp=200,semanticHealth=health,epoch=epoch)
 else:
  plan=http(control,'/incremental-plan?sourceConfigRef='+SOURCE)
  assert plan['state']=='READY' and plan['parentChainRef']==LATEST and plan['baseFullRef']==FULL,'CURRENT_SOURCE_PLAN_CHANGED'
  actual=dict(plan=plan)
 rows.append(dict(service=row['service'],pid=pid,sourceCommit=row['sourceCommit'],fileManifestSha256=row['fileManifestSha256'],installedFilesVerified=True,controlConfigurationPin=row['controlConfigurationPin'],**actual))
custody=verify_installation_receipt_custody(CUSTODY) if CUSTODY is not None else None
assert sum(pin['bytes'] for pin in HISTORY)<=512*1024*1024,'ORIGINAL_HISTORY_BUDGET_EXCEEDED'
for pin in HISTORY:
 path=pathlib.Path(pin['path']);assert path.resolve()==path and not path.is_symlink()
 raw=path.read_bytes();assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'],'IMMUTABLE_ORIGINAL_HISTORY_CHANGED'
history=dict(originalProtectedFiles=HISTORY_COUNT,immutableOriginalPathsVerified=len(HISTORY),allImmutableOriginalPathsUnchanged=True,
 originalActiveReceiptArchived=(custody['originalReceiptArchived'] if custody else None))
print(json.dumps(dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),controllers=rows,currentCustody=custody,currentProtectedHistory=history,businessMutationDispatched=False,controlApiQueriesPerformed=True,queryAuditWritesMayOccur=True)))
'''


def verify_control_query_effects(report):
 """Control GETs may append query audit metadata; no business mutation is sent."""
 assert report.get('status')=='PASS' and 'serverWrites' not in report,'CONTROL_QUERY_EFFECTS_REPORT_REQUIRED'
 assert report.get('businessMutationDispatched') is False,'CONTROL_BUSINESS_MUTATION_DISPATCHED'
 assert report.get('controlApiQueriesPerformed') is True and report.get('queryAuditWritesMayOccur') is True,'CONTROL_QUERY_AUDIT_EFFECTS_REQUIRED'


def current_remote_controls(installations, automatic):
 from install_automatic_57 import SCRIPT as install_script
 from installation_history_custody import SCRIPT as custody_script
 tree=ast.parse(install_script)
 probe=next(ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='health_probe' for target in node.targets))
 original_epoch="r=replacement_value(o,sys.argv[3]);assert r['backupEpoch']==c['sourceEpochPolicies'][sys.argv[2]]"
 assert probe.count(original_epoch)==1,'HEALTH_PROBE_EPOCH_CONTRACT_CHANGED'
 probe=probe.replace(original_epoch,"""r=replacement_value(o,sys.argv[3]);expected_policy=json.loads(sys.argv[4])
if expected_policy is None:
 assert 'backupEpoch' not in r and sys.argv[2] not in c.get('sourceEpochPolicies',{}),'UNREGISTERED_SOURCE_EPOCH_PRESENT'
else:
 assert r['backupEpoch']==expected_policy,'REGISTERED_SOURCE_EPOCH_CHANGED'""")
 result={}
 source=installations['source57']
 for suffix in ('57','58','59'):
  if suffix=='57':
   controls=[dict(row,**controller_generation(source,index)) for index,row in enumerate(source['controllers'])]
   controls[1].update(targetConfigRef='intruoyi-main-57-safe-restore-20261105-v2',epochPolicy=source['policy'],epoch=source['epoch'])
   custody=None
  else:
   installed=installations['targets'][suffix]
   controls=[dict(installed,pid=installed['controlPid'])];custody=installed['extendedCustody']
  original=json.loads((TASK/('protected-history-'+suffix+'.json')).read_text(encoding='utf-8'))
  assert original['status']=='PASS' and len(original['evidencePins'])==original['protectedFiles']
  history=original['evidencePins']
  if custody is not None:
   assert custody['originalActiveReceiptPin'] in history
   history=[pin for pin in history if pin!=custody['originalActiveReceiptPin']]
  values=dict(CONTROLLERS=controls,SOURCE=SOURCE,
   LATEST=automatic['operationIds']['I2'],FULL=automatic['operationIds']['FULL'],HEALTH_PROBE=probe,CUSTODY=custody,
   HISTORY=history,HISTORY_COUNT=original['protectedFiles'])
  script='\n'.join(key+'='+repr(value) for key,value in values.items())+'\n'+custody_script+'\n'+CURRENT_SCRIPT
  result[suffix]=remote('172.30.30.'+suffix,script,timeout=240)
  verify_control_query_effects(result[suffix])
 return result


def local_spug(installations, module):
 from install_automatic_spug import docker,CONTAINER,RUNTIME,entry
 installed=installations['spug']
 assert entry()==installed['newEntryPid'],'SPUG_ENTRY_PID_CHANGED'
 for name,pin in installed['files'].items():
  raw=(RUNTIME/name).read_bytes()
  assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['installedSha256'],'CURRENT_SPUG_FILE_CHANGED'
 container=json.loads(docker('inspect',CONTAINER))[0]
 assert container['Id']==installed['containerId'] and container['HostConfig']['PortBindings']['80/tcp']==[dict(HostIp='127.0.0.1',HostPort='18080')]
 prior=TASK.parent/'20261105-spug-full-to-prod'
 plan=json.loads((module.PRIVATE/'production-route-plan.private.json').read_bytes())
 settings=module.docker(module.READ)
 assert settings==plan['settings'],'SPUG_REGISTERED_SETTINGS_CHANGED'
 assert json.loads((module.RUNTIME/'private/smallapp-bridge.private.json').read_bytes())==plan['bridge'],'SPUG_BRIDGE_BINDINGS_CHANGED'
 for name,value in plan['files'].items():
  assert json.loads((module.RUNTIME/'private'/name).read_bytes())==value,'SPUG_TARGET_BINDING_CHANGED'
 return dict(status='PASS',sourceCommit=installed['sourceCommit'],entryPid=installed['newEntryPid'],fileCount=len(installed['files']),
  exactSpugSettingsAndRoutesVerified=True,loopback18080Verified=True)


def production_transports(module):
 original=module.read('local-transport-baseline.json');current=module.ports([42657,18557,43657])
 assert current[:2]==original['transports'],'ORIGINAL_SOURCE_OR_PROGRESS_TRANSPORT_CHANGED'
 receipt=module.read('transport-installation.json');stable=Path(receipt['stablePath'])
 assert stable.resolve().parent==module.PRIVATE.resolve() and stable.name=='production_control_transport.ps1'
 assert hashlib.sha256(stable.read_bytes()).hexdigest()==receipt['sha256']
 assert stable.read_bytes()==(module.TASK/'production_control_transport.ps1').read_bytes()
 live=json.loads((module.PRIVATE/'transport-production.json').read_bytes())
 assert live['target']=='172.30.30.57' and live['controlPort']==43657
 assert current[2]['pid']==live['sshPid'] and current[2]['parentPid']==live['supervisorPid']
 # Reuse only the original read-only task/process verifier; not its stale adapter hash or target generation.
 tree=ast.parse((module.TASK/'verify_local_control.py').read_text(encoding='utf-8'))
 function=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='closeout')
 expression=next(node.value for node in function.body if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='check' for target in node.targets))
 script=eval(compile(ast.Expression(expression),'<original-transport-check>','eval'),dict(str=str,live=live))
 assert subprocess.check_output([module.POWERSHELL,'-NoProfile','-Command',script],timeout=40).decode('utf-8-sig').strip()=='PASS'
 return dict(status='PASS',transports=current,stableScriptVerified=True,stableTaskRunning=True)


if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--record-selection',action='store_true');parser.add_argument('--source-installation');parser.add_argument('--catalogue-report');parser.add_argument('--catalogue-observation');args=parser.parse_args()
 if args.record_selection:
  assert args.catalogue_report and args.catalogue_observation and args.source_installation
  path=TASK/'automatic-current-installations.json';assert not path.exists(),'CURRENT_SELECTION_ALREADY_RECORDED'
  selection=dict(schemaVersion='TaskCurrentInstallations/v2',source57=file_pin(TASK,args.source_installation),
   spug=file_pin(TASK,'automatic-spug-installation-0d44578.json'),targets={s:file_pin(TASK,'automatic-target-installation-'+s+'.json') for s in ('58','59')},
   catalogueInstallation=file_pin(TASK,args.catalogue_report),catalogueReadonlyObservation=file_pin(TASK,args.catalogue_observation))
  write(path,selection)
  print(json.dumps(dict(status='SELECTION_RECORDED_NOT_VERIFIED',serverWrites=False)));raise SystemExit(0)
 assert not args.catalogue_report and not args.catalogue_observation and not args.source_installation
 installations=current_installations(TASK);automatic=automatic_chain(TASK)
 point=json.loads((TASK/'new-incremental-point-verified.json').read_text(encoding='utf-8'))
 operations={}
 for suffix in ('58','59'):
  value=json.loads((TASK/('restore-'+suffix+'-native-evidence.json')).read_text(encoding='utf-8'))
  assert value['status']=='PASS' and value['backupOperationId']==point['operationId'] and value['actualExitCode']==0
  operations[suffix]=value['operationId']
 prior=TASK.parent/'20261105-spug-full-to-prod';sys.path.insert(0,str(prior))
 spec=importlib.util.spec_from_file_location('stable_control_verification',prior/'verify_local_control.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 production=production_transports(module);spug=local_spug(installations,module)
 baseline=json.loads((TASK/'target-transports-current-baseline.json').read_text(encoding='utf-8'))
 assert baseline['status']=='PASS' and baseline['verificationMode']=='CAPTURED_ACTUAL_EXISTING_INSTALLATION' and baseline['target58And59ForwardingSemanticsReviewed']
 transport_pin=baseline['stableTransportPin']
 assert transport_pin['path']=='C:/Spug/runtime/private/restore-targets-20261104/restore_control_transport.ps1' and len(transport_pin['sha256'])==64 and int(transport_pin['sha256'],16)>=0 and transport_pin['bytes']>0
 script=SCRIPT.replace('TRANSPORT_SHA_LITERAL',transport_pin['sha256']).replace('TRANSPORT_BYTES_LITERAL',str(transport_pin['bytes']))
 raw=subprocess.check_output([module.POWERSHELL,'-NoProfile','-Command',script],timeout=40)
 targets=json.loads(raw.decode('utf-8-sig'));assert len(targets)==2
 current=current_remote_controls(installations,automatic)
 # Catalogue evidence and current runtime are independent of historical failed page observations.
 from catalogue_current_verification import verify_current_catalogue
 catalogue=verify_current_catalogue(installations['catalogue'],installations['source57'])
 assert catalogue['status']=='PASS' and catalogue['runtimeFilesAndProcessesVerified'] is True
 report=dict(status='PASS',observedAt=now(),backupOperationId=point['operationId'],targetRestoreOperationIds=operations,
  automaticOperationIds=automatic['operationIds'],production=production,spug=spug,targets=targets,currentControls=current,catalogue=catalogue,
  currentInstallationEvidenceVerified=True,catalogueCurrentRuntimeVerified=True,currentInstallationSelectionPin=file_pin(TASK,'automatic-current-installations.json'),
  targetTransportBaselinePin=transport_pin,anyServiceRestarted=False,anyRestoreDispatched=False,
  businessMutationDispatched=False,controlApiQueriesPerformed=True,queryAuditWritesMayOccur=True)
 write(TASK/'stable-controls-closeout.json',report);print(json.dumps(report))
