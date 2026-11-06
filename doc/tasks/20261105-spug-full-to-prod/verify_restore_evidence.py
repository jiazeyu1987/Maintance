"""Check this restore's original terminal and pinned native readback evidence.

Does not replay a restore, rehash the large archive, or expose business rows.
"""
import json
from install_prod_control import remote, TASK

SCRIPT = r'''
import datetime,hashlib,json,os,pathlib
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3')
request=REQUEST_LITERAL
full=FULL_LITERAL
verified=[]
def read(reference):
 assert 0<reference['bytes']<=32*1024*1024,'DOCUMENT_SIZE_OUT_OF_SCOPE'
 raw=pathlib.Path(reference['path']).read_bytes()
 assert len(raw)==reference['bytes'] and hashlib.sha256(raw).hexdigest()==reference['sha256'],'PIN_CHANGED'
 verified.append(reference)
 return json.loads(raw)
operation=request['operationId']
completion=json.loads((root/'ledger'/operation/'completion.json').read_bytes())
assert completion['operationId']==operation and completion['result']['state']=='SUCCEEDED'
assert completion['terminal']['actualExitCode']==0
result=read(completion['terminal']['resultPin'])
assert result['schemaVersion']=='backup-restore-operation-result/v1'
assert result['operationId']==result['requestId']==operation and result['action']=='RESTORE'
assert result['state']=='SUCCEEDED' and result['failureCode'] is None and result['actualExitCode']==0
data=result['data']
assert request['recoveryPointRef']==full['operationId']
assert data['targetConfigRef']==request['targetConfigRef']=='intruoyi-main-57-safe-restore-20261105-v2'
assert data['recoveryPoint']==full['commonRecoveryPoint']
assert len(data['orderedChainPins'])==1 and data['orderedChainPins'][0]['sha256']==full['pointPin']['sha256']
assert len(data['databaseResultPins'])==len(data['objectResultPins'])==1
database=read(data['databaseResultPins'][0]);comparison=read(database['comparisonPin'])
assert database['fullSchemaDataEquivalenceVerified'] is True
assert comparison['state']=='SCHEMA_DATA_EQUAL_PENDING_APPLICATION_PROOF' and comparison['fullSchemaDataEquivalenceVerified'] is True
assert database['recoveryPoint']==data['recoveryPoint']
objects=read(data['objectResultPins'][0]);object_comparison=read(objects['comparisonPin'])
assert objects['originalVersionIdsPreserved'] is True and objects['recoveryPoint']==data['recoveryPoint']
assert object_comparison['state']=='PHYSICAL_VERSION_READBACK_MATCH_PENDING_FULL_RESTORE_PROOF'
assert object_comparison['exactVersionIdentityVerified'] is True
consistent=read(data['consistencyPin'])
assert consistent['schemaVersion']=='RecoveryConsistencyEvidence/v1' and consistent['recoveryPoint']==data['recoveryPoint']
assert consistent['databaseResultPin']==data['databaseResultPins'][0] and consistent['objectResultPin']==data['objectResultPins'][0]
assert consistent['presentReferencesVerified'] is True and consistent['invariantsVerified'] is True
assert consistent['sourceMissingBaselinePreserved'] is True
assert consistent['allReferencesVerified']==(consistent['sourceMissingReferenceCount']==0)
derived=read(data['derivedPin'])
assert derived['recoveryPoint']==data['recoveryPoint']
redis=[item for item in derived['classes'] if item['className']=='redis']
assert len(redis)==1 and redis[0]['classification']=='RESTORE'
redis_readback=read(redis[0]['observationPin'])
assert redis_readback['schemaVersion']=='RedisDumpRestoreReadback/v1'
assert redis_readback['valuesVerified'] is True and redis_readback['absoluteExpiryVerified'] is True
application=read(data['applicationStartPin'])
assert application['state']=='SUCCEEDED' and application['isolation']=='REGISTERED_MAIN_RESOURCE_CUSTODY'
assert application['programImagesChanged'] is False
replacement=read(data['replacementReceiptPin'])
assert replacement['state']=='SUCCEEDED' and replacement['operationId']==operation and replacement['targetConfigRef']==request['targetConfigRef']
cleanup=read(data['stagingCleanupPin'])
assert cleanup['schemaVersion']=='OperationStagingCleanup/v1' and cleanup['state']=='SUCCEEDED'
assert cleanup['operationId']==operation and pathlib.Path(cleanup['root']).name==operation
assert pathlib.Path(cleanup['root'])==root/'recovery-operations'/operation
assert cleanup['deletedFiles']==len(cleanup['files']) and cleanup['deletedBytes']==sum(f['bytes'] for f in cleanup['files'])
assert all(not (pathlib.Path(cleanup['root'])/p).exists() for p in cleanup['selectedPaths'])
release_path=root/'recovery-operations'/operation/'resource-release.json'
release_raw=release_path.read_bytes()
assert 0<len(release_raw)<=1024*1024
release_pin={'path':str(release_path),'bytes':len(release_raw),'sha256':hashlib.sha256(release_raw).hexdigest()}
release=read(release_pin)
assert release['reason']=='VALIDATED_CHILD_SUCCESS'
assert release['resultPin'] in result['originalResultPins'] and release['exitPin'] in result['originalResultPins']
native_result=read(release['resultPin'])
assert native_result['operationId']==operation and native_result['state']=='SUCCEEDED' and native_result['actualExitCode']==0
assert native_result['data']==data
readiness_pins=[]
installed=json.loads((root/'target-installation.json').read_bytes())
target=read(installed['ownerConfigurationPin'])['targets'][request['targetConfigRef']]
services={service['role']:service for service in target['services']}
for role,directory,port,path in [('minio','objects',9000,'/minio/health/ready'),('backend','final',48081,'/actuator/health'),('frontend','final',80,'/')]:
 healthpath=root/'recovery-operations'/operation/directory/('main-health-'+role+'.json')
 raw=healthpath.read_bytes();reference=dict(path=str(healthpath),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
 assert reference in native_result['originalResultPins'],'MAIN_HEALTH_ORIGINAL_PIN_MISSING'
 health=read(reference);service=services[role]
 assert health['schemaVersion']=='RegisteredMainSemanticReadiness/v1' and health['role']==role
 assert health['containerId']==service['id'] and health['imageId']==service['imageId']
 assert health['serviceConfigurationDigest']==target['mainApplication']['serviceConfigurationDigests'][role]
 assert health['endpoint']=='http://'+service['ip']+':'+str(port)+path
 assert health['status']=='healthy' and health['ready'] is True and health['httpStatus']==200
 assert health['semanticStatus']==('UP' if role=='backend' else 'READY') and health['attempts']>=1
 assert not health['dockerHealthcheckConfigured'] or health['dockerHealthStatus']=='healthy'
 readiness_pins.append(reference)
exited=read(release['exitPin'])
assert exited['actualExitCode']==0 and exited['timedOut'] is False
reservation=read(release['reservationPin'])
assert reservation['operationId']==operation and reservation['targetConfigRef']==request['targetConfigRef']
assert not os.path.lexists('/var/lib/spug-restore-resources/active.json')
report={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'operationId':operation,'backupOperationId':full['operationId'],'targetConfigRef':request['targetConfigRef'],'state':result['state'],'finishedAt':result['finishedAt'],'actualExitCode':0,'sameNewFullPointVerified':True,'database':{'uuid':database['databaseUuid'],'fullSchemaDataEquivalenceVerified':True,'tableCount':len(comparison['tables']),'totalRows':sum(t['rows'] for t in comparison['tables'].values()),'schemaSha256':comparison['schemaSha256']},'objects':{k:object_comparison[k] for k in ('exactVersionIdentityVerified','versionCount','deleteMarkerCount','totalVersionBytes','uniqueContentCount','versionHistorySha256')},'consistency':{k:consistent[k] for k in ('allReferencesVerified','presentReferencesVerified','sourceMissingReferenceCount','sourceMissingBaselinePreserved','invariantsVerified')},'redis':{k:redis_readback[k] for k in ('restoredKeyCount','expiredBeforeRestoreCount','independentlyVerifiedKeyCount','valuesVerified','absoluteExpiryVerified')},'applicationStart':{'state':application['state'],'isolation':application['isolation'],'businessAcceptance':application['businessAcceptance']},'replacementState':replacement['state'],'cleanupFields':sorted(cleanup),'verifiedDocumentPins':len(verified),'independentBusinessUIRequired':True,'status':'PASS'}
archive_release=read(data['archiveViewReleasePin'])
assert archive_release['schemaVersion']=='ArchiveViewProtectionRelease/v1'
assert archive_release['operationId']==operation and archive_release['originalMountRestored'] is True
fence_release=read(data['publishedWriteFenceReleasePin'])
assert fence_release['operationId']==operation
assert fence_release['originalRulesPreserved'] is True
report['archiveViewRestored']=True
report['publishedWriteFenceReleased']=True
report['hostResourceReservationReleased']=True
scheduler_release=read(data['mysqlSchedulerReleasePin'])
assert scheduler_release['schemaVersion']=='MainMysqlSchedulerRelease/v1'
assert scheduler_release['operationId']==operation and scheduler_release['originalStateRestored'] is True
assert scheduler_release['originalState']=='ON'
scheduler_intent=read(scheduler_release['intentPin']);scheduler_active=read(scheduler_release['activePin'])
assert scheduler_intent['operationId']==scheduler_active['operationId']==operation
assert scheduler_intent['originalState']=='ON' and scheduler_active['pausedState']=='OFF'
assert scheduler_active['intentPin']==scheduler_release['intentPin']
report['mysqlSchedulerOriginalStateRestored']=True
report['mysqlSchedulerOriginalState']=scheduler_release['originalState']
report['mysqlSchedulerReleasePin']=data['mysqlSchedulerReleasePin']
report['resourceReleasePin']=release_pin
report['mainSemanticReadinessVerified']=True
report['mainReadinessPins']=readiness_pins
report['verifiedDocumentPins']=len(verified)
print(json.dumps(report))
'''

if __name__ == '__main__':
    request=json.loads((TASK/'restore-ui-submission.json').read_text(encoding='utf-8'))['request']
    full=json.loads((TASK.parent/'20261104-spug-prod-full-to-test'/'new-full-point-verified.json').read_text(encoding='utf-8'))
    script=SCRIPT.replace('REQUEST_LITERAL',repr(request)).replace('FULL_LITERAL',repr(full))
    report=remote(script,timeout=55)
    (TASK/'restored-native-evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report))
