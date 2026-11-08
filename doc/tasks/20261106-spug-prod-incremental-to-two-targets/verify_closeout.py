"""Require this new incremental and both real complete-chain restorations."""
import datetime,hashlib,json,re,subprocess
from pathlib import Path
import closeout_contracts as contracts
from common import TASK,PRIVATE,now,write,restore_kind,allocator_installation,allocator_contract_name
from observe_closeout_hosts import i2_binding
from verify_stable_controls import verify_control_query_effects

def read(name):return json.loads((TASK/name).read_text(encoding='utf-8'))
def moment(value):return datetime.datetime.fromisoformat(value.replace('Z','+00:00'))

def verify_automatic_source_preservation(task,preserved,operation_id):
 binding=i2_binding(task,preserved['observedAt'])
 assert preserved['status']=='PASS' and preserved['backupOperationId']==operation_id==binding['backupOperationId'],'FINAL_SOURCE_PRESERVATION_OPERATION_CHANGED'
 assert preserved['automaticI2EvidencePins']==binding['automaticI2EvidencePins'],'FINAL_SOURCE_PRESERVATION_EVIDENCE_CHANGED'

def terminal_observation(kind,request):
 return contracts.terminal_observation(TASK,kind,request)
def success_submission(kind,action,point=None,suffix=None):
 request=read(kind+'-ui-submission.json')['request'];ui=read(kind+'-ui-result.json');terminal=read(kind+'-terminal-record.json')
 assert request['action']==action and request['sourceConfigRef']=='intruoyi-57-safe-20261024-v1'
 if point:assert request['recoveryPointRef']==point
 if suffix:assert request['targetConfigRef']=='intruoyi-main-'+suffix+'-safe-restore-20261104-v1'
 assert ui['realLogin'] and ui['writes']==1 and ui['request']==request
 assert not ui['blocked'] and not ui['pageErrors']
 reconciled=kind==restore_kind('58') and ui['status']=='FAIL' and ui['error']=='TimeoutError: page.waitForResponse: Timeout 45000ms exceeded while waiting for event "response"'
 if reconciled:
  assert 'httpStatus' not in ui,'DO_NOT_SUBSTITUTE_UNKNOWN_POST_STATUS'
  for phase in ('accepted','terminal'):
   observed=read(kind+'-ui-readonly-'+phase+'.json')
   assert observed['status']=='PASS' and observed['realBrowser'] and observed['businessWrites']==0 and observed['request']==request
   assert observed['exactHistoryRowCount']==1 and observed['catalogueHttp']==200 and not observed['pageErrors'] and not observed.get('queryError') and not observed['problem']
   assert observed['spugHistoryId']==terminal['spugHistoryId'] and moment(observed['observedAt'])>moment(ui['finishedAt'])
   if phase=='terminal':assert observed['state']=='SUCCEEDED'
   for endpoint in ('/backup-entry-api/operations/','/backup-entry-api/progress/'):
    assert any(r['endpoint']==endpoint+request['operationId'] and r['httpStatus']==200 for r in observed['httpObservations'])
  assert all(v in (dict(path='/release-center/api/applications/intruoyi/package-catalog',status=504),dict(path='/backup-entry-api/progress/'+request['operationId'],status=409),dict(path='/backup-entry-api/operations/'+request['operationId'],status=409)) for v in ui['httpFailures'])
 else:
  assert ui['status']=='PASS' and ui['httpStatus']==202
  if kind in ('restore-58-r4','restore-59'):
   observed=terminal_observation(kind,request)
   assert observed['status']=='PASS' and observed['realBrowser'] and observed['businessWrites']==0 and observed['request']==request
   assert observed['exactHistoryRowCount']==1 and observed['catalogueHttp']==200 and not observed['pageErrors'] and not observed.get('queryError') and not observed['problem']
   assert observed['spugHistoryId']==terminal['spugHistoryId'] and observed['state']=='SUCCEEDED' and moment(observed['observedAt'])>moment(ui['finishedAt'])
   for endpoint in ('/backup-entry-api/operations/','/backup-entry-api/progress/'):
    assert any(r['endpoint']==endpoint+request['operationId'] and r['httpStatus']==200 for r in observed['httpObservations'])
 if ui['httpFailures'] and not reconciled:
  if kind=='restore-58-r4':
   assert ui['httpFailures']==[dict(path='/release-center/api/applications/intruoyi/package-catalog',status=504)],'UNRESOLVED_UI_HTTP_FAILURE'
   catalogue=read('restore-58-r4-catalogue-readonly-verification.json')
   assert catalogue['documentHttpStatus']==200 and catalogue['endpoint']=='/release-center/api/applications/intruoyi/package-catalog'
   assert moment(catalogue['responseObservedAt'])>=moment(catalogue['observedAt']) and moment(catalogue['finishedAt'])>=moment(catalogue['responseObservedAt'])
  else:
   assert kind=='incremental-3' and ui['httpFailures']==[dict(path='/release-center/api/applications/intruoyi/package-catalog',status=502)],'UNRESOLVED_UI_HTTP_FAILURE'
   catalogue=read('catalogue-readonly-verification.json')
  assert catalogue['status']=='PASS' and catalogue['httpStatus']==200 and catalogue['actualPageRequest'] and catalogue['backupPageInitialized'] and catalogue['businessWrites']==0
  assert moment(catalogue['observedAt'])>=moment(ui['finishedAt']),'CATALOGUE_RECOVERY_NOT_INDEPENDENTLY_OBSERVED'
 assert terminal['request']==request and terminal['result']['state']=='SUCCEEDED'
 assert terminal['result']['operationId']==request['operationId']
 assert read(kind+'-live-progress.json')['writes']==0
 return request

if __name__=='__main__':
 point=read('new-incremental-point-verified.json');operation=point['operationId']
 assert point['status']=='PASS' and point['state']=='SUCCEEDED' and point['actualExitCode']==0 and point['pointType']=='INCREMENTAL'
 request=success_submission('incremental-4','INCREMENTAL')
 assert request['operationId']==operation and request['parentChainRef']==point['parentBackupId']=='smallapp-7fec29a3e132463096aec915c08acab3'
 assert len(point['parentPointPins'])==1 and point['database']['allCurrentTableDataObserved']
 payload=read('new-incremental-payload-readback.json')
 assert payload['status']=='PASS' and payload['operationId']==operation and payload['pointPin']==point['pointPin'] and payload['manifestPin']==point['manifestPin']
 assert payload['payloadContentVerified'] and payload['exactTreeVerifiedBeforeAndAfter'] and payload['metadataPinsVerifiedBeforeAndAfter']
 assert payload['serverDurabilityVerified'] is False and payload['nativeLegacySchemaPreserved']
 assert payload['encrypted'] and payload['signingRequired'] and payload['privateConnectionCache'] and payload['connectionClosed']
 assert payload['payloadFiles']==point['payloadFiles'] and payload['payloadBytes']==point['payloadBytes']
 assert payload['verificationMode']=='NATIVE_FULL_READBACK_EVIDENCE_AUDIT'
 source=read('source-after-backup-preservation.json');flags=read('source-global-state-restored.json')
 assert source['status']==flags['status']=='PASS' and source['backupOperationId']==flags['backupOperationId']==operation
 assert flags['originalGlobalStateRestored'] and flags['strictBinlogToolStillVerified'] and flags['failedOriginalFilesPreserved']==10044
 exporter=read('binlog-tmpfs-tool-provisioned.json');installation=read('source-control-binlog-temp-installation.json');native_export=read('binlog-tmpfs-full-native-export.json')
 assert exporter['status']==installation['status']==native_export['status']=='PASS'
 assert flags['registeredExporterTemporaryContractVerified'] and flags['exporterDescriptorPin']==exporter['descriptorPin']==installation['exporterDescriptorPin']==native_export['descriptorPin']
 assert flags['activeCaptureConfigurationPin']==installation['captureConfigurationPin'] and source['ownedAddedExportersVerified'] and source['ownedAddedExporterCount']==3
 assert native_export['actualNativeAllSegmentsExported'] and native_export['allActualExitCodesZero'] and native_export['totalStderrBytes']==0
 assert moment(source['observedAt'])>=moment(point['finishedAt']) and moment(flags['observedAt'])>=moment(point['finishedAt'])
 failure=read('incremental-364-failure.json');terminals=[v for v in failure['terminalDocuments'] if v['path'].endswith('/result.json') or v['path'].endswith('/terminal-result.json')]
 assert len(terminals)==2 and all(v['state']=='FAILED_RETAINED' and v['actualExitCode']==1 and v['failureCode']=='MINIMAL_BINLOG_TOOL_CHANGED' for v in terminals)
 second=read('incremental-2-terminal-record.json')
 assert second['result']['state']=='FAILED' and second['result']['errorCode']=='FORMAL_CAPTURE_PIPE_DEADLINE'
 assert read('failed-365-all-files-preserved.json')['protectedFiles']==9090
 third=read('incremental-3-terminal-record.json')
 assert third['result']['state']=='FAILED' and third['result']['errorCode']=='FORMAL_CAPTURE_STDERR_LIMIT'
 assert read('failed-366-all-files-preserved.json')['protectedFiles']==916
 third_failure=read('incremental-366-failure.json')
 third_terminals=[v for v in third_failure['terminalDocuments'] if v['path'].endswith('/result.json') or v['path'].endswith('/terminal-result.json')]
 assert len(third_terminals)==2 and all(v['state']=='FAILED_RETAINED' and v['actualExitCode']==1 and v['failureCode']=='FORMAL_CAPTURE_STDERR_LIMIT' for v in third_terminals)
 catalogue=read('catalogue-readonly-verification.json')
 assert catalogue['status']=='PASS' and catalogue['httpStatus']==200 and catalogue['actualPageRequest'] and catalogue['businessWrites']==0
 restored={}
 for suffix in ('58','59'):
  contract=read(allocator_contract_name(suffix));assert contract['status']=='PASS' and contract['incrementalDatabaseDdlScopeV3Supported'] and contract['packageFilesMatch'] and contract['frozenAllocatorRestoreSupported']
  installed=allocator_installation(suffix);assert installed['sourceCommit']==read(('packaged-frontend' if suffix=='58' else 'frontend-health')+'-implementation-commit.json')['implementationCommit']
  assert installed['actualHealthContractVerified'] and contract['actualHealthContractVerified']
  if suffix=='58':assert installed['actualPackagedConstructorVerified'] and contract['actualPackagedConstructorVerified']
  request=success_submission(restore_kind(suffix),'RESTORE',operation,suffix);native=read('restore-'+suffix+'-native-evidence.json');runtime=read('restored-runtime-'+suffix+'.json')
  assert native['status']=='PASS' and native['state']=='SUCCEEDED' and native['actualExitCode']==0 and native['operationId']==request['operationId'] and native['backupOperationId']==operation
  assert native['sameNewIncrementalAndFullParentChainVerified'] and native['databaseStepCount']==2 and native['mergedPhysicalObjectStepCount']==1
  assert native['frozenAllocator']['stateVerified'] and native['frozenAllocator']['fullSchemaAndDataComparisonUnchanged'] and native['frozenAllocator']['changedTableCount']==native['frozenAllocator']['actualNativeMutationCount']
  database=native['database'];assert database['baseFullSchemaDataEquivalenceVerified'] and database['incrementalReplayAndAffectedDataVerified'] and database['allCurrentTableDataVerified'] and database['nativeIncrementalFullSchemaDataEquivalenceFlag'] is False
  assert database['tableCount']==point['database']['currentBaseTables'] and native['objects']['exactVersionIdentityVerified']
  assert all(native['consistency'][k] for k in ('allReferencesVerified','presentReferencesVerified','sourceMissingBaselinePreserved','invariantsVerified'))
  assert native['redis']['valuesVerified'] and native['redis']['absoluteExpiryVerified']
  assert native['configuredProtectionsVerified'] and native['hostResourceReservationReleased'] and native['mysqlScheduler']['originalStateRestored']
  assert native['authorizedInstallationReceiptCustodyVerified'] and native['installationReceiptCustody']['status']=='PASS'
  assert native['installationReceiptCustody']['selectedCurrentReceiptPin']==installed['currentReceiptPin']
  for configured,result_field in [('archive','archiveViewRestored'),('published','publishedWriteFenceReleased')]:
   assert native[result_field] is (True if native['protectionConfiguration'][configured] else None)
  assert native['applicationStart']['state']=='SUCCEEDED' and native['replacementState']=='SUCCEEDED'
  assert runtime['status']=='PASS' and runtime['operationId']==request['operationId'] and runtime['backendHealth']=='UP' and runtime['frontendHTTP']==200 and runtime['minioReadyHTTP']==200
  assert runtime['mysqlGlobalState']['originalStateRestored'] and runtime['allConfiguredDockerHealthchecksHealthy'] and runtime['installedConfigurationPinsUnchanged']
  assert len(runtime['services'])==5 and all(s['running'] for s in runtime['services'])
  before=read('target-'+suffix+'-before-business.json');after=read('target-'+suffix+'-after-business.json')
  assert before['status']==after['status']=='PASS' and after['realLogin'] and after['businessMutations']==0
  assert after['businessPage']['visibleRows']>0 and after['businessPage']['totalRows']==before['businessPage']['totalRows'] and after['version']==before['version']
  assert moment(after['observedAt'])>=moment(native['finishedAt'])
  preserved=read('target-'+suffix+'-preservation.json');assert preserved['status']=='PASS' and preserved['allOriginalDefinitionsAndImagesPreserved'] and preserved['otherBusinessRuntimePreserved'] and preserved['fstabPreserved'] and preserved['protectedMountsPreserved']
  assert moment(preserved['observedAt'])>=moment(native['finishedAt'])
  assert moment(read(restore_kind(suffix)+'-ui-submission.json')['submittedAt'])>=moment(source['observedAt'])
  restored[suffix]=dict(operationId=request['operationId'],database=database,objects=native['objects'],businessVersion=after['version'],businessUserTotal=after['businessPage']['totalRows'])
 assert {k:v for k,v in restored['58']['database'].items() if k!='uuid'}=={k:v for k,v in restored['59']['database'].items() if k!='uuid'}
 assert restored['58']['objects']==restored['59']['objects']
 assert moment(read(restore_kind('59')+'-ui-submission.json')['submittedAt'])>=moment(read('target-58-after-business.json')['observedAt'])
 final_restore_finished=max(moment(read('restore-'+s+'-native-evidence.json')['finishedAt']) for s in ('58','59'))
 old=read('restore-58-terminal-record.json');assert old['result']['state']=='FAILED' and old['result']['errorCode']=='FORMAL_SCHEMA_MISMATCH'
 second=read('restore-58-r2-terminal-record.json');assert second['result']['state']=='FAILED' and second['result']['errorCode']=='MAIN_HEALTH_ENDPOINT_INVALID'
 third=read('restore-58-r3-terminal-record.json');assert third['result']['state']=='FAILED' and third['result']['errorCode']=='MAIN_FRONTEND_READINESS_INVALID'
 failed=read('failed-368-closeout-preservation.json')
 assert failed['status']=='PASS' and failed['protectedFiles']==2916 and failed['protectedBytes']==47497557606
 assert failed['allThreeOriginalFailuresUnchanged'] and failed['exactFailureConsumerChain']==[
  'smallapp-c21bb7ce9f5b4668b850c37a80964786','smallapp-b4f35606e4854516960050a76473038b',
  'smallapp-e61ca1c4b93f4aa3ab5a70eca399c36d',restored['58']['operationId']]
 assert failed['originalFailureUnchanged'] and failed['exactSamePointClearanceConsumedOnce'] and failed['allOriginalBytesRead']
 assert failed['newOperationId']==restored['58']['operationId'] and moment(failed['observedAt'])>=final_restore_finished
 for suffix in ('57','58','59'):
  history=read('protected-history-verified-'+suffix+'.json');assert history['status']=='PASS'
  original_history=read('protected-history-'+suffix+'.json')
  assert history['allImmutableOriginalPathsUnchanged'] and history['allOriginalBytesPreserved']
  assert history['originalProtectedFileCount']==history['protectedFiles']==original_history['protectedFiles']
  assert history['protectedBytes']==original_history['protectedBytes']
  if suffix in ('58','59'):
   custody=history['installationReceiptCustody'];assert custody['status']=='PASS' and custody['authorizedActiveReceiptCount']==1
   assert custody['originalReceiptArchived'] and custody['allReceiptAndConfigurationPinsVerified'] and custody['allHistoricalSourceAndTargetDefinitionsUnchanged']
   assert custody['activationCount']==(5 if suffix=='58' else 2) and history['immutableOriginalPathsVerified']+1==history['protectedFiles']
   assert custody['selectedCurrentReceiptPin']==allocator_installation(suffix)['currentReceiptPin']
  else:assert history['installationReceiptCustody'] is None and history['immutableOriginalPathsVerified']==history['protectedFiles']
  assert moment(history['observedAt'])>=final_restore_finished
  preserved=read(('source' if suffix=='57' else 'target-'+suffix)+'-closeout-preservation.json')
  assert preserved['status']=='PASS' and moment(preserved['observedAt'])>=final_restore_finished
  assert preserved['allOriginalDefinitionsAndImagesPreserved'] and preserved['otherBusinessRuntimePreserved'] and preserved['fstabPreserved'] and preserved['protectedMountsPreserved']
 stable=read('stable-controls-closeout.json');assert stable['status']=='PASS' and stable['backupOperationId']==operation and stable['targetRestoreOperationIds']=={s:r['operationId'] for s,r in restored.items()}
 unused=read('unused-exporters-stopped.json');inventory=read('source-added-exporters.json')
 assert unused['status']=='PASS' and unused['backupOperationId']==operation and unused['registeredExporterRunning'] and unused['allOriginalAndRegisteredContainersPreserved']
 assert {r['containerId'] for r in unused['containers']}=={r['containerId'] for r in inventory['containers'] if not r['registered']}
 assert len(unused['containers'])==2 and all(r['stopped'] and r['retained'] for r in unused['containers'])
 assert moment(read('source-closeout-preservation.json')['observedAt'])>=moment(unused['observedAt'])
 automatic=contracts.automatic_chain(TASK)
 verify_automatic_source_preservation(TASK,read('source-closeout-preservation.json'),automatic['operationIds']['I2'])
 assert stable['automaticOperationIds']==automatic['operationIds'] and stable['currentInstallationEvidenceVerified'] and stable['catalogueCurrentRuntimeVerified']
 assert moment(stable['observedAt'])>=moment(automatic['finalFinishedAt'])
 assert stable['currentInstallationSelectionPin']==contracts.file_pin(TASK,'automatic-current-installations.json')
 current_installations=contracts.current_installations(TASK)
 for suffix in ('57','58','59'):
  current=stable['currentControls'][suffix];original=read('protected-history-'+suffix+'.json')
  verify_control_query_effects(current)
  assert current['currentProtectedHistory']['allImmutableOriginalPathsUnchanged']
  assert current['currentProtectedHistory']['originalProtectedFiles']==original['protectedFiles']
  assert current['currentProtectedHistory']['immutableOriginalPathsVerified']==original['protectedFiles']-(0 if suffix=='57' else 1)
  if suffix!='57':assert current['currentCustody']['selectedCurrentReceiptPin']==current_installations['targets'][suffix]['currentReceiptPin']
  latest_preservation=read(('source' if suffix=='57' else 'target-'+suffix)+'-closeout-preservation.json')
  assert moment(latest_preservation['observedAt'])>=max(final_restore_finished,moment(automatic['finalFinishedAt'])),'POST_AUTOMATIC_PRESERVATION_REQUIRED'
 cleanup=read('owned-build-cleanup.json');entries=contracts.owned_builds(TASK)
 assert cleanup['status']=='PASS' and cleanup['deleted'] and cleanup['ownedBuildManifestPin']==contracts.file_pin(TASK,'task-owned-builds.json')
 assert {row['generation'] for row in cleanup['builds']}=={row['generation'] for row in entries} and len(cleanup['builds'])==len(entries)
 registrations=subprocess.check_output(['git','worktree','list','--porcelain'],cwd=TASK.parents[2]).decode().replace('\\','/').lower()
 for entry in entries:
  result=next(row for row in cleanup['builds'] if row['generation']==entry['generation'])
  assert result['status']=='PASS' and result['deleted'] and not result['newCommits'] and not result['mergeRequired']
  assert result['buildReportPin']==entry['reportPin'] and result['targetCommit']==entry['targetCommit']
  assert result['worktree']==entry['worktree'] and result['retainedPackageSha256']==entry['packageSha256']
  assert result['physicalPathAbsent'] and result['gitRegistrationAbsent'] and result['automaticOperationIds']==automatic['operationIds']
  owned=Path(entry['worktree']).resolve()
  assert owned.parent==PRIVATE.resolve() and not owned.exists() and owned.as_posix().lower() not in registrations
 report=dict(status='PASS',observedAt=now(),automaticBackupChain=automatic,ownedBuildCount=len(entries),currentControlGenerationsIndependentlyVerified=True,backupOperationId=operation,parentBackupId=point['parentBackupId'],newIncrementalNativeExitCode=0,completeParentChainRestoredToBothTargets=True,fullSafePayloadReadbackVerified=True,sourceOriginalStateRestored=True,targets=restored,allOriginalDefinitionsAndOtherBusinessPreserved=True,companyShareAndFstabPreserved=True,previousFailedOriginalsRetained=True,failedOriginalFilesPreserved=10044,registeredExporterTemporaryContractVerified=True,unusedFailedExporterContainersStoppedAndRetained=True,stableControlsVerified=True,ownedBuildPhysicalAndGitRegistrationAbsent=True,successfulBackupUiHttpFailures=0,historicalReleaseCatalogueErrorRetainedAndIndependent200Verified=True,serverDurabilityVerified=False)
 write(TASK/'closeout-verification.json',report);print(json.dumps(report))
