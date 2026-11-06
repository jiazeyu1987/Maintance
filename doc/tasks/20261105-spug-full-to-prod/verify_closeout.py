"""Require complete real production restoration and owned cleanup evidence."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

from install_prod_control import TASK, PRIVATE, POINT, TARGET
from test_storage_linux import ROOT, DOCKER

def read(name):
    return json.loads((TASK/name).read_text(encoding='utf-8'))

def moment(value):
    return datetime.datetime.fromisoformat(value.replace('Z','+00:00'))

if __name__=='__main__':
    request=read('restore-ui-submission.json')['request'];operation=request['operationId']
    assert request['action']=='RESTORE' and request['recoveryPointRef']==POINT and request['targetConfigRef']==TARGET
    ui=read('restore-ui-result.json')
    assert ui['realLogin'] and ui['writes']==1 and ui['request']==request and not ui['blocked'] and not ui['pageErrors']
    if ui['status']=='PASS':
        assert ui['httpStatus']==202;dispatch='HTTP202_OBSERVED'
    else:
        assert ui['status']=='FAIL' and 'Timeout' in ui['error'] and 'httpStatus' not in ui
        dispatch='ORIGINAL_TIMEOUT_RETAINED_NATIVE_ACCEPTANCE_VERIFIED'
    terminal=read('restore-terminal-record.json')
    assert terminal['result']['state']=='SUCCEEDED' and terminal['result']['operationId']==operation
    native=read('restored-native-evidence.json')
    assert native['status']=='PASS' and native['operationId']==operation
    assert native['state']=='SUCCEEDED' and native['actualExitCode']==0 and native['backupOperationId']==POINT
    assert native['targetConfigRef']==TARGET and native['sameNewFullPointVerified']
    assert native['database']['fullSchemaDataEquivalenceVerified'] and native['objects']['exactVersionIdentityVerified']
    assert all(native['consistency'][k] for k in ['allReferencesVerified','presentReferencesVerified','sourceMissingBaselinePreserved','invariantsVerified'])
    assert native['redis']['valuesVerified'] and native['redis']['absoluteExpiryVerified']
    assert native['archiveViewRestored'] and native['publishedWriteFenceReleased'] and native['hostResourceReservationReleased']
    assert native['mysqlSchedulerOriginalStateRestored'] and native['mysqlSchedulerOriginalState']=='ON'
    failure=read('failed-attempt-preservation.json')
    assert failure['status']=='PASS' and failure['remoteOriginalPinsUnchanged']==205 and failure['localOriginalPinsUnchanged']>=8
    assert failure['operationId']=='smallapp-181aec2e16c94e259f875c0e64eb863a'
    assert operation!=failure['operationId'] and moment(failure['observedAt'])>=moment(native['finishedAt'])
    second_failure=read('health-failed-attempt-preservation.json')
    assert second_failure['status']=='PASS' and second_failure['remoteOriginalPinsUnchanged']==703 and second_failure['localOriginalPinsUnchanged']==8
    assert second_failure['operationId']=='smallapp-d7a963eb1e9a4c16826c92d5753b30c3'
    assert second_failure['successfulNewOperationId']==operation and moment(second_failure['observedAt'])>=moment(native['finishedAt'])
    assert native['mainSemanticReadinessVerified'] and len(native['mainReadinessPins'])==3
    previous=json.loads((TASK.parent/'20261105-spug-prod-full-to-review/restored-native-evidence.json').read_text(encoding='utf-8'))
    assert previous['status']=='PASS' and previous['backupOperationId']==POINT
    assert {k:v for k,v in native['database'].items() if k!='uuid'}=={k:v for k,v in previous['database'].items() if k!='uuid'}
    assert native['objects']==previous['objects'] and native['redis']==previous['redis']
    preserved=read('preservation-full-point-verified.json');payload=read('preservation-full-payload-readback.json')
    assert preserved['state']=='SUCCEEDED' and payload['status']=='PASS' and payload['operationId']==preserved['operationId']
    assert payload['payloadContentVerified'] and payload['exactTreeVerifiedBeforeAndAfter'] and payload['metadataPinsVerifiedBeforeAndAfter']
    assert payload['manifestPin']==preserved['manifestPin'] and payload['pointPin']==preserved['pointPin']
    assert payload['payloadFiles']==preserved['payloadFiles'] and payload['payloadBytes']==preserved['payloadBytes']
    assert payload['encrypted'] and payload['signingRequired'] and payload['privateConnectionCache'] and payload['connectionClosed']
    assert payload['verificationMode']=='NATIVE_FULL_READBACK_EVIDENCE_AUDIT'
    assert payload['nativeLegacySchemaPreserved'] and payload['serverDurabilityVerified'] is False
    admission=read('preservation-full-admission.json')
    assert admission['newRecoveryPointRef']==preserved['operationId'] and admission['newPointAdmitted']
    source=read('preserved-source-runtime.json');before=read('target-production-before-restore-business.json')
    assert source['status']=='PASS' and source['backupPublicationVerified'] and source['databaseOriginalWriteFlagsRestored']
    assert before['status']=='PASS' and before['realLogin'] and before['businessMutations']==0
    assert moment(source['observedAt'])>=moment(preserved['finishedAt'])
    assert moment(before['observedAt'])>=moment(preserved['finishedAt'])
    assert moment(payload['observedAt'])>=moment(preserved['finishedAt'])
    assert moment(payload['finishedAt'])<=moment(read('restore-ui-submission.json')['submittedAt'])
    for name in ['restored-runtime.json','protection-runtime-verification.json','local-control-closeout.json']:
        report=read(name);assert report['status']=='PASS' and report['operationId']==operation
        assert moment(report['observedAt'])>=moment(native['finishedAt'])
    runtime=read('restored-runtime.json')
    assert runtime['backendHealth']=='UP' and runtime['frontendHTTP']==200 and len(runtime['services'])==5
    assert all(s['running'] for s in runtime['services'])
    after=read('target-production-after-restore-business.json')
    assert after['status']=='PASS' and after['realLogin'] and after['businessMutations']==0 and after['businessPage']['visibleRows']>0
    expected_page=json.loads((TASK.parent/'20261105-spug-prod-full-to-review/target-review-after-restore-business.json').read_text(encoding='utf-8'))
    assert after['version']==expected_page['version'] and after['businessPage']['totalRows']==expected_page['businessPage']['totalRows']
    assert moment(after['observedAt'])>=moment(native['finishedAt'])
    choices=read('three-targets-ui-verification.json')
    assert choices['status']=='PASS' and choices['realLogin'] and choices['realBrowser']
    assert choices['operationId']==operation and choices['restorePosts']==0 and not choices['blocked']
    assert {c['host'] for c in choices['choices']}=={'172.30.30.57','172.30.30.58','172.30.30.59'}
    assert len(choices['choices'])==3 and all(c['exactSourceAndPointVerified'] and c['overwriteAcknowledgementRequired'] for c in choices['choices'])
    assert moment(choices['observedAt'])>=moment(native['finishedAt'])
    for name in ['other-business-after-restore.json','other-business-closeout.json']:
        report=read(name);assert report['status']=='PASS' and report['allOriginalDefinitionsAndImagesPreserved']
        assert report['otherBusinessRuntimePreserved'] and report['otherBusinessContainerCount']==190
        assert report['fstabPreserved'] and report['originalStagePreserved'] and moment(report['observedAt'])>=moment(native['finishedAt'])
    registrations=subprocess.check_output(['git','worktree','list','--porcelain'],cwd=ROOT).decode().replace('\\','/').lower()
    builds=[]
    for name,count in [('release-build-db64656.json',123),('release-build-bdd8aab.json',124),('release-build-9b3a298.json',124),('release-build-1595d0f.json',125),('release-build-9dce318.json',126)]:
        report=read(name);path=Path(report['worktree']).resolve()
        assert report['status']=='PASS' and report['allFilesShaAndCompileVerified'] and report['fileCount']==count
        assert not report['newCommits'] and not report['mergeRequired'] and report['deleted']
        assert path.parent==PRIVATE.resolve() and not path.exists() and path.as_posix().lower() not in registrations
        builds.append(dict(worktree=str(path),targetCommit=report['targetCommit'],physicalAndGitRegistrationAbsent=True))
    cleanup=read('owned-resource-cleanup.json')
    assert cleanup['status']=='PASS' and cleanup['operationId']==operation and cleanup['ownedTestContainerRemoved'] and cleanup['ownedTestVolumeRemoved']
    label='codex.task=spug-full-to-prod-20261105'
    assert not subprocess.check_output([DOCKER,'ps','-aq','--filter','label='+label]).strip()
    assert not subprocess.check_output([DOCKER,'volume','ls','-q','--filter','label='+label]).strip()
    original_failure_count=0
    prior=TASK.parent/'20261105-spug-prod-full-to-review'
    for name in ['failed-attempt-preservation.json','second-failed-attempt-preservation.json','third-failed-attempt-preservation.json']:
        for pin in json.loads((prior/name).read_text(encoding='utf-8'))['pins']:
            path=(prior/pin['path']).resolve();assert path.is_relative_to(prior.resolve())
            raw=path.read_bytes();assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256']
            original_failure_count+=1
    assert original_failure_count==28
    result=dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),operationId=operation,
                nativeExitCode=0,realSpugSubmissionCount=1,dispatchObservation=dispatch,preservedCurrentDataFullReadbackVerified=True,
                fullSelectedPointRestored=True,realBusinessLoginVerified=True,otherBusinessPreserved=True,
                ownedBuilds=builds,ownedTestContainersAndVolumesAbsent=True,stableLocalAndRemoteRuntimeVerified=True,
                originalPriorFailureFilesUnchanged=28,serverDurabilityVerified=False)
    (TASK/'closeout-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))
