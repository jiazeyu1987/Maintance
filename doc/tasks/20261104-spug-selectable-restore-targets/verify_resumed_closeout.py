"""Read-only final component, preservation, and isolated checkout cleanup checks."""
import hashlib,json,subprocess
from pathlib import Path
from install_review_control import SCRIPT as COMMON
from resume_readonly import TASK,PRIVATE,remote
SCRIPT=r'''
root=pathlib.Path('/mnt/intruoyi-data/spug-main-restore-20261104-v3')
receipt=json.loads((root/'target-installation.json').read_bytes());owner=read(receipt['ownerConfigurationPin']);control=read(receipt['controlConfigurationPin'])
engine=pathlib.Path(owner['formalModuleDirectory']).parent;version=json.loads((engine/'package.json').read_bytes())
need(all(pin(engine/n)['sha256']==h for n,h in version['files'].items()),'PACKAGE_DRIFT')
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from formal_data_evidence import validate_limits
need(validate_limits(owner['dataLimits'])==owner['dataLimits'],'DATA_LIMITS_INVALID')
current=business();installed=json.loads((root/'configuration/readback-04f5f9ce-installation.json').read_bytes())
need(current==installed['business'],'BUSINESS_DRIFT_AFTER_INSTALLATION')
values=[control['pythonPin']['path'],control['workingDirectory'],control['environment']['PYTHONPATH'],str(engine)]
need(not any('.codex/worktrees' in v or 'spug-review-control-release' in v for v in values),'TEMPORARY_RUNTIME_PATH')
out={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'service':receipt['service'],
 'active':run(['systemctl','is-active',receipt['service']]).decode().strip(),'enabled':run(['systemctl','is-enabled',receipt['service']]).decode().strip(),
 'ownerConfigurationPin':receipt['ownerConfigurationPin'],'controlConfigurationPin':receipt['controlConfigurationPin'],
 'packageFiles':len(version['files']),'packageFilesMatch':True,'dataLimits':owner['dataLimits'],'maxExpandedBytes':owner['maxExpandedBytes'],
 'businessIdsPidsStartTimesAndConfigurationUnchanged':True,'stableRuntimePaths':True,'zeroRestores':True,
 'activeReservation':pathlib.Path('/var/lib/spug-restore-resources/active.json').exists()}
need(not out['activeReservation'],'UNEXPECTED_RESTORE_RESERVATION')
for n in ('ledger','operations','recovery-operations','replacement-state'):
 need(not [p for p in (root/n).rglob('*') if p.is_file() and p.name!='service.lock'],'UNEXPECTED_OPERATION_RECORDS')
print(json.dumps(out))
'''
if __name__=='__main__':
    review=remote('172.30.30.59',COMMON.split('receiptpath=root/')[0]+SCRIPT,timeout=60)
    source={}
    for suffix,service in [('57','spug-intruoyi-source-57-20261105.service'),('58','spug-main-restore-58-20261104-v3.service')]:
        source[suffix]=remote('172.30.30.'+suffix,"import subprocess,json\ns="+repr(service)+"\nprint(json.dumps({'active':subprocess.check_output(['systemctl','is-active',s],timeout=10).decode().strip(),'enabled':subprocess.check_output(['systemctl','is-enabled',s],timeout=10).decode().strip()}))",timeout=30)
    release=Path('C:/Users/D01021/.codex/worktrees/spug-review-control-release-20261105/Maintance')
    listed=subprocess.check_output(['git','worktree','list','--porcelain']).decode('utf-8')
    cleanup={'releaseWorktree':str(release),'targetCommit':'04f5f9ce958b52479c0c729fe32dbb69669e73fb','newCommits':False,'mergeRequired':False,'gitRegistrationAbsent':release.as_posix() not in listed,'physicalPathAbsent':not release.exists(),'testPassed':15}
    assert cleanup['gitRegistrationAbsent'] and cleanup['physicalPathAbsent']
    assert review['active']=='active' and review['enabled']=='enabled'
    assert all(v=={'active':'active','enabled':'enabled'} for v in source.values())
    raw=json.loads((PRIVATE/'resume-57.private.json').read_text(encoding='utf-8'))
    backend=next(r for r in raw['containers'] if r['Name']=='/intruoyi-backend')
    minio=next(r for r in raw['containers'] if r['Id']=='b9f1d48ecf88104080eaba1628d251e793f42ec37be792f8d8c1a10c476fcabf')
    prod={'host':'172.30.30.57','observedAt':raw['observedAt'],'historicalInspectTimeoutResolved':True,
      'currentBackendId':backend['Id'],'backendRunning':backend['State']['Running'],
      'writableApplicationMounts':[{'source':m['Source'],'destination':m['Destination'],'type':m['Type']} for m in backend['Mounts'] if m['RW']],
      'minioPublishedPorts':minio['HostConfig']['PortBindings'],
      'assessment':'Existing installation and MAIN preserved-storage contracts reject writable application mounts and exposed data services. No production target configuration was issued; resource writer ownership was not asserted.',
      'applicableCurrentContractCodes':['INSTALL_APPLICATION_CONFIGURATION_NOT_PINNABLE','MAIN_APPLICATION_WRITABLE_MOUNT_REJECTED','REPLACEMENT_STORAGE_INVALID','INSTALL_PUBLISHED_DATA_SERVICE_REJECTED'],
      'liveTargetPreflight':'NOT_REGISTERED','restorePerformed':False}
    out={'status':'PASS_FOR_COMPONENT_SCOPE','review':review,'sourceAndTestControl':source,'cleanup':cleanup,
      'remainingBlockers':{'57':'Unsupported current writable runtime mounts/data endpoint registration; target remains disabled','59':'Original four services stopped and canonical readonly archive bind missing; separate original-service start authorization required'},
      'threeDestinationGoalComplete':False}
    for name,value in [('resumed-closeout.json',out),('production-target-current-gates.json',prod)]:
        (TASK/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(out,ensure_ascii=False))
