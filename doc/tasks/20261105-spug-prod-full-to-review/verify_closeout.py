"""Require the real restore, readbacks, UI and owned cleanup before closeout."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
from preflight import TASK, PRIVATE, POINT, TARGET
from test_recovery_linux import DOCKER

def read(name):
    return json.loads((TASK/name).read_text(encoding='utf-8'))

def moment(value):
    return datetime.datetime.fromisoformat(value.replace('Z','+00:00'))

if __name__=='__main__':
    request=read('restore-ui-submission.json')['request'];operation=request['operationId']
    assert request['recoveryPointRef']==POINT and request['targetConfigRef']==TARGET
    ui=read('restore-ui-result.json')
    assert ui['status']=='PASS' and ui['realLogin'] and ui['writes']==1 and ui['httpStatus']==202
    assert ui['request']==request and not ui['blocked']
    terminal=read('restore-terminal-record.json')
    assert terminal['result']['state']=='SUCCEEDED' and terminal['result']['operationId']==operation
    native=read('restored-native-evidence.json')
    runtime=read('restored-runtime.json');preserved=read('preservation-verification.json')
    source=read('source-preservation-verification.json');page=read('target-review-after-restore-business.json')
    for report in (native,runtime,preserved,source,page):assert report['status']=='PASS'
    for report in (native,runtime,preserved):assert report['operationId']==operation
    assert native['state']=='SUCCEEDED' and native['actualExitCode']==0 and native['backupOperationId']==POINT
    assert native['sameNewFullPointVerified'] and native['database']['fullSchemaDataEquivalenceVerified']
    assert native['protectedOriginalFailurePinsUnchanged']==203 and native['hostResourceReservationReleased']
    assert runtime['backendHealth']=='UP' and runtime['frontendHTTP']==200
    assert len(runtime['services'])==5 and all(row['running'] for row in runtime['services'])
    assert preserved['restoreOperationCount']==4 and preserved['otherBusinessRuntimePreserved']
    assert preserved['controlActiveEnabled'] and preserved['stableRuntimePaths'] and preserved['archiveReadOnly']
    assert source['originalFiveContainersImagesPidsAndStartTimesPreserved'] and source['backendHealth']=='UP' and source['frontendHTTP']==200
    assert page['realLogin'] and page['businessMutations']==0 and page['businessPage']['visibleRows']>0
    baseline=read('target-review-before-restore-2-business.json')
    assert page['version']==baseline['version'] and page['businessPage']['totalRows']==baseline['businessPage']['totalRows']
    assert moment(source['observedAt'])>=moment(native['finishedAt'])
    assert moment(page['observedAt'])>=moment(native['finishedAt'])
    registrations=subprocess.check_output(['git','worktree','list','--porcelain'],cwd=TASK.parents[2]).decode().replace('\\','/').lower()
    builds=[]
    for name in ('release-build-verification.json','dependency-release-build-verification.json',
                 'network-release-build-76bb60b-verification.json','network-release-build-verification.json'):
        report=read(name);path=Path(report['worktree']).resolve()
        assert report['status']=='PASS' and report['allFilesShaAndCompileVerified'] and report['fileCount']==122
        assert not report['newCommits'] and not report['mergeRequired'] and report['deleted']
        assert path.parent==PRIVATE.resolve() and not path.exists() and path.as_posix().lower() not in registrations
        builds.append(dict(worktree=str(path),targetCommit=report['targetCommit'],physicalAndGitRegistrationAbsent=True))
    assert not subprocess.check_output([DOCKER,'ps','-aq','--filter','label=codex.task=spug-prod-full-to-review-20261105']).strip()
    assert not subprocess.check_output([DOCKER,'volume','ls','-q','--filter','label=codex.task=spug-prod-full-to-review-20261105']).strip()
    local_count=0
    for name in ('failed-attempt-preservation.json','second-failed-attempt-preservation.json','third-failed-attempt-preservation.json'):
        for pin in read(name)['pins']:
            path=(TASK/pin['path']).resolve();assert path.is_relative_to(TASK.resolve())
            raw=path.read_bytes();assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'];local_count+=1
    assert local_count==28
    report=dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS',operationId=operation,
        nativeExitCode=0,realSpugSubmissionCount=1,realBusinessLoginVerified=True,sourcePreserved=True,
        otherBusinessPreserved=True,ownedBuilds=builds,ownedTestContainersAndVolumesAbsent=True,
        stableRuntimeVerified=True,originalLocalFailureFilesUnchanged=local_count,
        developmentWorktreeRetainedForSeparateBlockedTargetTask=True)
    (TASK/'closeout-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
