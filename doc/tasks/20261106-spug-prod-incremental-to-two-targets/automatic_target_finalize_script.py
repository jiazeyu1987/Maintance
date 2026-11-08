"""Finalize the exact already-running generation; no staging or restart path."""
import ast
from automatic_targets_install_script import SCRIPT


BODY=r'''
root=pathlib.Path(CANDIDATE['previousCustody']['root']);generation='automatic-'+COMMIT[:7]
unit=CANDIDATE['service'];target_ref=CANDIDATE['targetConfigRef'];engine=pathlib.Path(CANDIDATE['engine'])
need(SUFFIX=='58' and CANDIDATE['host']==FINALIZE_PROOF['host']=='172.30.30.58','FINALIZE_TARGET_INVALID')
need(CANDIDATE['sourceCommit']==COMMIT and FINALIZE_PROOF['noControlApiCalled'] is True and FINALIZE_PROOF['serverWrites'] is False,'FINALIZE_OBSERVATION_REQUIRED')
need(FINALIZE_PROOF['controlPin']==CANDIDATE['controlConfigurationPin'] and FINALIZE_PROOF['ownerPin']==CANDIDATE['ownerConfigurationPin'],'FINALIZE_GENERATION_CHANGED')
oldowner=read(CANDIDATE['oldOwnerPin']);oldcontrol=read(CANDIDATE['oldControlPin'])
newcontrol=read(CANDIDATE['controlConfigurationPin']);owner=read(CANDIDATE['ownerConfigurationPin'])
need(newcontrol==CANDIDATE['control'] and owner==CANDIDATE['owner'],'FINALIZE_CANDIDATE_CHANGED')
need(owner['targets']==oldowner['targets'] and owner['sources']==oldowner['sources'] and newcontrol['sourceConfigurations']==oldcontrol['sourceConfigurations'],'FINALIZE_HISTORICAL_CONFIGURATION_CHANGED')
target=oldowner['targets'][target_ref];oldengine=pathlib.Path(oldowner['formalModuleDirectory']).parent
oldpackage=read(pin(oldengine/'package.json'));version=read(FINALIZE_PROOF['stagedPackage']['packagePin'])
need(len(version['files'])==130 and version['packageSha256']==CANDIDATE['fileManifestSha256'],'FINALIZE_PACKAGE_CHANGED')
need({str(p.relative_to(engine)) for p in engine.rglob('*') if p.is_file()}==set(version['files'])|{'package.json'},'FINALIZE_PACKAGE_FILE_SET_CHANGED')
need(all(pin(engine/name)['sha256']==sha for name,sha in version['files'].items()),'FINALIZE_PACKAGE_BYTES_CHANGED')
need(all(pin(oldengine/name)['sha256']==sha for name,sha in oldpackage['files'].items()),'FINALIZE_OLD_PACKAGE_CHANGED')
policy=CANDIDATE['targetBackupEpochPolicy'];need(policy is None,'FINALIZE_EPOCH_SCOPE_INVALID');epoch=None
receiptpath=root/'target-installation.json';receipt=read(CANDIDATE['oldActiveReceiptPin']);previous=CANDIDATE['previousReceiptPin']
need(read(previous)==receipt and pin(receiptpath)==CANDIDATE['oldActiveReceiptPin'],'FINALIZE_RECEIPT_STATE_CHANGED')
need(len(FINALIZE_PROOF['newDropins'])==1,'FINALIZE_DROPIN_AMBIGUOUS')
dropinpin=FINALIZE_PROOF['newDropins'][0];need(pin(dropinpin['path'])==dropinpin,'FINALIZE_DROPIN_CHANGED');dropin=pathlib.Path(dropinpin['path'])
need(dropin.parent==pathlib.Path('/etc/systemd/system')/(unit+'.d') and dropin.name.endswith('-'+generation+'.conf'),'FINALIZE_DROPIN_SCOPE_INVALID')
audit_pins={pathlib.Path(item['pin']['path']).name:item['pin'] for item in FINALIZE_PROOF['auditFiles']}
expected_audit_root=root/'configuration'/('installation-audit-'+generation+'-resume-1')
need(all(pathlib.Path(ref['path']).parent==expected_audit_root for ref in audit_pins.values()),'FINALIZE_AUDIT_ROOT_CHANGED')
business=read(audit_pins['business-before.json']);strict_rows=read(audit_pins['strict-history-before-activation.json'])
prior_rows=read(audit_pins['history-before-source-idle.json']);after_rows=read(audit_pins['history-after-source-idle.json'])
query_audit=read(audit_pins['source-idle-query-audit.json'])
need(query_audit['beforePin']==audit_pins['history-before-source-idle.json'] and query_audit['afterPin']==audit_pins['history-after-source-idle.json']
 and query_audit['sourceIdle']['status']=='PASS' and query_audit['sourceIdle']['originalTerminalStatesVerified'] is True
 and query_audit['sourceIdle']['sourceConfigRef']==SOURCE and strict_rows==after_rows,'FINALIZE_SOURCE_IDLE_PROOF_CHANGED')
rechecked_audit=verify_query_append(prior_rows,after_rows,pathlib.Path(oldcontrol['ledgerRoot']),SOURCE)
need(all(query_audit[key]==item for key,item in rechecked_audit.items()),'FINALIZE_QUERY_AUDIT_CHANGED')
before=business['containers'];fstab=business['fstabPin'];beforemounts=business['mounts'];oldpid=business['oldControlPid']
need(oldpid==CANDIDATE['oldControlPid'] and business['oldOwnerPin']==CANDIDATE['oldOwnerPin']
 and business['oldControlPin']==CANDIDATE['oldControlPin'] and business['oldActiveReceiptPin']==CANDIDATE['oldActiveReceiptPin'],'FINALIZE_BUSINESS_BASELINE_CHANGED')
protected_paths=['/mnt/nas',*target['dataPaths'],*oldowner['sources'][SOURCE]['archiveRoots']]
history_roots={pathlib.Path(oldcontrol['ledgerRoot']),pathlib.Path(oldcontrol['registryRoot']),pathlib.Path(oldowner['operationsRoot']),pathlib.Path(target['replacement']['stateRoot'])}
history={path:tuple(row['identity'][:4]+row['identity'][6:]) for path,row in strict_rows.items()}
preactivation_ref=FINALIZE_PROOF['constructor-preactivation-'+generation+'-resume-1']['pin'];preactivation=read(preactivation_ref)
need(preactivation['ownerConfigurationPin']==CANDIDATE['ownerConfigurationPin'] and preactivation['targetConfigRef']==target_ref
 and preactivation['noDatabaseIO'] is True and preactivation['restoreDispatched'] is False,'FINALIZE_PREACTIVATION_PROOF_CHANGED')
for ref in preactivation['nativeInvocationPins']:
 proof=read(ref);need(proof['mutation'] is False and proof['actualExitCode']==0,'FINALIZE_PREACTIVATION_NOT_READ_ONLY')
newpid=FINALIZE_PROOF['pid'];ownerpin=CANDIDATE['ownerConfigurationPin'];controlpin=CANDIDATE['controlConfigurationPin']
argv=[newcontrol['pythonPin']['path'],'-B',str(engine/'control_entry.py'),'serve','--config-pin',canonical(controlpin).decode()]
def ready_process():
 need(active_pid()==newpid and (pathlib.Path('/proc')/str(newpid)/'cmdline').read_bytes().decode().rstrip('\0').split('\0')==argv,'FINALIZE_CONTROL_IDENTITY_CHANGED')
def listener():
 sockets=set()
 for path in (pathlib.Path('/proc')/str(newpid)/'fd').iterdir():
  try:name=str(path.readlink())
  except FileNotFoundError:continue
  if name.startswith('socket:['):sockets.add(name[8:-1])
 matched=[]
 for table in ('tcp','tcp6'):
  for line in (pathlib.Path('/proc')/str(newpid)/'net'/table).read_text().splitlines()[1:]:
   row=line.split()
   if row[3]=='0A' and int(row[1].split(':')[1],16)==newcontrol['listenPort']:matched.append(row[9])
 need(matched and all(inode in sockets for inode in matched),'FINALIZE_LISTENER_NOT_OWNED')
def exact_history():
 return verify_saved_snapshot(strict_rows,history_roots)
def final_preserved():
 preserved();exact_history();ready_process();listener()
sys.path[:0]=oldcontrol['environment']['PYTHONPATH'].split(':')
from recovery_resource_admission import _host_lock
lock=os.open(target['replacement']['lockPath'],os.O_RDWR|os.O_NOFOLLOW);fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
with _host_lock():
 workers(newpid);reservation();ready_process();listener();final_preserved()
 custody_before=verify_installation_receipt_custody(CANDIDATE['previousCustody'])
 limits=next(line for line in pathlib.Path('/proc',str(newpid),'limits').read_text().splitlines() if line.startswith('Max open files'))
 need(limits.split()[3:5]==['65536','65536'],'FINALIZE_FD_LIMIT_CHANGED')
 process_environment=dict(part.split('=',1) for part in (pathlib.Path('/proc')/str(newpid)/'environ').read_bytes().decode().split('\0') if '=' in part)
 actual_argv=(pathlib.Path('/proc')/str(newpid)/'cmdline').read_bytes().decode().rstrip('\0').split('\0')
 runtime_environment=verify_control_runtime(process_environment,newcontrol['environment'],actual_argv,argv)
 module_names=[name for name in version['files'] if pathlib.PurePosixPath(name).name=='recovery_control_smallapp_native.py']
 need(len(module_names)==1,'FINALIZE_CONTROL_MODULE_AMBIGUOUS')
 worker_environment=observe_worker_environment(newcontrol['pythonPin']['path'],newcontrol['environment'],pin(engine/module_names[0]))
 selection=http_selection(newcontrol,ready_process)
 audit_root=root/'configuration'/('installation-audit-'+generation+'-finalize-1');need(not audit_root.exists(),'FINALIZE_ATTEMPT_EXISTS')
 audit_root.mkdir(mode=0o700);bound_proof=create(audit_root/'activated-resume-observation.json',canonical(FINALIZE_PROOF))
 newenv=dict(newcontrol['environment'])
 args=[controlpin,ownerpin,target_ref,SOURCE,str(root/'configuration'/('constructor-postactivation-'+generation+'-finalize-1')),policy]
 actual_gate=json.loads(run([newcontrol['pythonPin']['path'],'-B','-c',GATE,canonical(args).decode()],env=newenv,timeout=180))
 need(actual_gate['status']=='PASS','FINALIZE_CONSTRUCTOR_NOT_PROVEN');final_preserved();workers(newpid)
 need(pin(receiptpath)==CANDIDATE['oldActiveReceiptPin'],'FINALIZE_ACTIVE_RECEIPT_CHANGED_BEFORE_PUBLISH')
 updated=dict(receipt,sourceCommit=COMMIT,engine=str(engine),ownerConfigurationPin=ownerpin,controlConfigurationPin=controlpin)
 need(updated==CANDIDATE['proposedReceipt'],'FINALIZE_RECEIPT_CONTRACT_CHANGED')
 temporary=receiptpath.with_name('target-installation.'+generation+'.finalize-1.tmp')
 create(temporary,canonical(updated));os.replace(temporary,receiptpath);fsync_dir(root)
 current=pin(receiptpath);need(current==CANDIDATE['proposedCurrentReceiptPin'],'FINALIZE_PUBLISHED_RECEIPT_CHANGED')
 step=dict(sourceCommit=COMMIT,engine=str(engine),previousReceiptPin=previous,currentReceiptPin=current,
  ownerConfigurationPin=ownerpin,controlConfigurationPin=controlpin,dropinPin=dropinpin)
 custody=copy.deepcopy(CANDIDATE['previousCustody']);custody['steps'].append(step);custody['expectedGenerationCommits'].append(COMMIT)
 custody['selectedOwnerPin']=ownerpin;custody['selectedControlPin']=controlpin
 custody_after=verify_installation_receipt_custody(custody);final_preserved()
 out=dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),host=CANDIDATE['host'],targetConfigRef=target_ref,
  service=unit,**step,fileCount=130,packageSha256=CANDIDATE['packageSha256'],fileManifestSha256=CANDIDATE['fileManifestSha256'],
  oldControlPid=oldpid,controlPid=newpid,liveMaxOpenFiles=65536,epoch=epoch,epochPolicy=policy,epochStatus=CANDIDATE['epochStatus'],
  source57MetadataUnchanged=True,targetAndSourceConfigurationUnchanged=True,previousGenerationsRetained=True,
  allBusinessDefinitionsAndRuntimeUnchanged=True,originalContainerCount=len(before),fstabAndProtectedMountsUnchanged=True,
  originalHistoryIdentitiesPreserved=len(history),failedOriginalFilesPreserved=len(CANDIDATE['retainedHistoryPins']),
  resumedStagedGeneration=True,finalizedAlreadyActivatedGeneration=True,serviceRestartedDuringFinalization=False,sourceIdleRerunDuringFinalization=False,
  savedHistoryIdentityValidation=exact_history(),
  controlRuntimeEnvironment=runtime_environment,workerEnvironmentObservation=worker_environment,
  sourceIdlePerformedBeforeHostLock=True,sourceIdleQueryAuditPin=audit_pins['source-idle-query-audit.json'],
  strictHistorySnapshotPin=audit_pins['strict-history-before-activation.json'],originalBusinessSnapshotPin=audit_pins['business-before.json'],
  activatedFailureObservationPin=bound_proof,actualSelectionVerifiedBeforeActivation=True,actualSelectionVerifiedAfterActivation=True,
  actualHealthContractVerified=True,actualPackagedConstructorVerified=True,constructorStopsBeforeDatabaseIO=True,
  constructorEvidencePin=actual_gate['constructorEvidencePin'],candidateConstructorEvidencePin=preactivation_ref,
  currentTargetSelection=selection,beforeSemanticHealth=preactivation['semanticHealth'],installationReceiptCustodyBefore=custody_before,
  installationReceiptCustody=custody_after,extendedCustody=custody,noMutationReservationAbsent=True,restoreDispatched=False,backupDispatched=False)
 create(root/'configuration'/('installation-'+generation+'.json'),canonical(out));print(json.dumps(out))
os.close(lock)
'''


def finalization_script():
    names={'need','canonical','pin','read','run','create','fsync_dir','samebytes','identity','active_pid','workers',
           'reservation','docker','snapshot','mounts','history_identity','verify_retained','preserved','http_selection'}
    tree=ast.parse(SCRIPT)
    definitions=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in names]
    assert {node.name for node in definitions}==names
    imports='import copy,datetime,fcntl,hashlib,json,os,pathlib,stat,subprocess,sys,urllib.request\n'
    value=imports+'\n'.join(ast.get_source_segment(SCRIPT,node) for node in definitions)+'\n'+BODY
    compile(value,'<finalize-activated-target>','exec')
    return value
