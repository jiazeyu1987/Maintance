"""Audit two real database steps and merged objects for this exact increment."""
import argparse,ast,json
from common import TASK,remote,write,restore_kind,allocator_installation
from installation_history_custody import inputs as custody_inputs,SCRIPT as CUSTODY_SCRIPT

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('suffix',choices=['58','59']);args=parser.parse_args();suffix=args.suffix
 tree=ast.parse((TASK.parent/'20261105-spug-prod-full-to-review/verify_restore_evidence.py').read_text(encoding='utf-8'))
 script=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SCRIPT' for t in n.targets))
 script=script.replace("root=pathlib.Path('/mnt/intruoyi-data/spug-main-restore-20261104-v3')","root=pathlib.Path(ROOT)")
 script=script.replace("'intruoyi-main-59-safe-restore-20261104-v1'","TARGET")
 start=script.index("assert len(data['orderedChainPins'])==1")
 end=script.index("objects=read(",start)
 current=r'''assert data['orderedChainPins']==full['parentPointPins']+[full['pointPin']]
assert len(data['databaseResultPins'])==2 and len(data['objectResultPins'])==1
base=read(data['databaseResultPins'][0]);base_comparison=read(base['comparisonPin'])
assert base['fullSchemaDataEquivalenceVerified'] is True and base_comparison['state']=='SCHEMA_DATA_EQUAL_PENDING_APPLICATION_PROOF'
database=read(data['databaseResultPins'][1]);comparison=read(database['comparisonPin'])
assert database['fullSchemaDataEquivalenceVerified'] is False and database['incrementalReplayAndAffectedDataVerified'] is True
assert comparison['state']=='SCHEMA_AFFECTED_DATA_EQUAL_PENDING_APPLICATION_PROOF' and comparison['fullSchemaDataEquivalenceVerified'] is False
expected=read(full['database']['expectedDataPin']);observed=read(database['observedPin'])
assert expected['affectedTables']==observed['affectedTables'] and comparison['tables']==expected['tables']==observed['tables']
assert comparison['sourceObservationSha256']==expected['observationSha256'] and comparison['targetObservationSha256']==observed['observationSha256']
assert len(comparison['tables'])==full['database']['currentBaseTables'] and full['database']['allCurrentTableDataObserved'] is True
assert database['recoveryPoint']==data['recoveryPoint']
'''
 script=script[:start]+current+script[end:]
 script=script.replace("consistent['databaseResultPin']==data['databaseResultPins'][0]","consistent['databaseResultPin']==data['databaseResultPins'][-1]")
 script=script.replace("assert len(protected_failure_pins)==203","assert protected_failure_pins")
 script=script.replace('protectedOriginalFailurePinsUnchanged','protectedOriginalHistoryPinsUnchanged')
 script=script.replace("'sameNewFullPointVerified':True","'sameNewIncrementalAndFullParentChainVerified':True")
 script=script.replace("'fullSchemaDataEquivalenceVerified':True,'tableCount'","'baseFullSchemaDataEquivalenceVerified':True,'incrementalReplayAndAffectedDataVerified':True,'nativeIncrementalFullSchemaDataEquivalenceFlag':False,'allCurrentTableDataVerified':True,'tableCount'")
 insert=r'''
owner=read(INSTALL['ownerConfigurationPin']);control=read(INSTALL['controlConfigurationPin'])
configuration=json.loads((root/'recovery-operations'/operation/'configuration.json').read_bytes())
assert configuration['targets']==owner['targets'],'ORIGINAL_TARGET_CONFIGURATION_CHANGED'
main=owner['targets'][TARGET]['mainApplication']
archive_configured='archiveMountProtection' in main
published_configured=any(v['role']=='minio' for v in main.get('publishedDataEndpoints',[]))
assert ('archiveViewReleasePin' in data)==archive_configured
assert ('publishedWriteFenceReleasePin' in data)==published_configured
if archive_configured:
 archive_release=read(data['archiveViewReleasePin'])
 assert archive_release['schemaVersion']=='ArchiveViewProtectionRelease/v1' and archive_release['operationId']==operation and archive_release['originalMountRestored'] is True
if published_configured:
 fence_release=read(data['publishedWriteFenceReleasePin'])
 assert fence_release['operationId']==operation and fence_release['originalRulesPreserved'] is True
scheduler=read(data['mysqlSchedulerReleasePin'])
assert scheduler['schemaVersion']=='MainMysqlSchedulerRelease/v1' and scheduler['operationId']==operation and scheduler['originalStateRestored'] is True
assert scheduler['originalState']==BASELINE['database']['eventScheduler']
read(scheduler['intentPin']);read(scheduler['activePin'])
report['configuredProtectionsVerified']=True
report['archiveViewRestored']=True if archive_configured else None
report['publishedWriteFenceReleased']=True if published_configured else None
report['protectionConfiguration']=dict(archive=archive_configured,published=published_configured)
report['mysqlScheduler']=dict(originalState=scheduler['originalState'],originalStateRestored=True)
report['databaseStepCount']=2
report['mergedPhysicalObjectStepCount']=1
allocator_refs=[p for p in native_result['originalResultPins'] if p['path'].endswith('/database-001/allocator-result.json')]
assert len(allocator_refs)==1,'FROZEN_ALLOCATOR_RESULT_REQUIRED'
allocator=read(allocator_refs[0]);intent=read(allocator['intentPin'])
assert allocator['schemaVersion']=='FrozenAutoIncrementRestoreResult/v1' and allocator['frozenAllocatorStateVerified'] is True
assert allocator['fullDataEquivalenceVerified'] is False and allocator['changedTableCount']==len(allocator['changePins'])==len(intent['changes'])
assert intent['sourceSchemaSha256']==expected['schema']['schemaSha256'] and intent['sourceObservationSha256']==expected['schema']['observationSha256']
before=read(intent['targetSchemaBeforePin'])
assert intent['targetIdentity']==before['observationIdentity'] and before['observationIdentity']['databaseUuid']==database['databaseUuid']
for reference,change in zip(allocator['changePins'],intent['changes']):
 receipt=read(reference);assert receipt==dict(**change,verified=True)
calls=[]
for reference in native_result['originalResultPins']:
 p=pathlib.Path(reference['path'])
 if p.parent==pathlib.Path(allocator_refs[0]['path']).parent and p.name.startswith('native-'):
  value=read(reference)
  if value['mutation']:
   assert value['state']=='SUCCEEDED' and value['actualExitCode']==0 and value['stderrBytes']==0 and value['finishedAt']
   calls.append(value)
assert len(calls)==allocator['changedTableCount'],'ALLOCATOR_NATIVE_MUTATION_COUNT_CHANGED'
report['frozenAllocator']=dict(stateVerified=True,changedTableCount=allocator['changedTableCount'],
 actualNativeMutationCount=len(calls),frozenSourceSchemaSha256=intent['sourceSchemaSha256'],fullSchemaAndDataComparisonUnchanged=True)
assert HEALTH_CONTRACT['status']=='PASS' and HEALTH_CONTRACT['actualHealthContractVerified']
services={s['role']:s for s in owner['targets'][TARGET]['services']}
readiness={}
for role in ('minio','backend','frontend'):
 refs=[p for p in native_result['originalResultPins'] if p['path'].endswith('/main-health-'+role+'.json')]
 assert len(refs)==1,'EXACT_NATIVE_SEMANTIC_READINESS_REQUIRED'
 proof=read(refs[0]);service=services[role]
 assert proof['schemaVersion']=='RegisteredMainSemanticReadiness/v1' and proof['role']==role
 assert proof['containerId']==service['id'] and proof['imageId']==service['imageId']
 assert proof['serviceConfigurationDigest']==main['serviceConfigurationDigests'][role]
 assert proof['endpoint']==HEALTH_CONTRACT['healthEndpoints'][role]
 assert proof['ready'] and proof['httpStatus']==200 and proof['status']=='healthy'
 assert proof['semanticStatus']==('UP' if role=='backend' else 'READY')
 assert not proof['dockerHealthcheckConfigured'] or proof['dockerHealthStatus']=='healthy'
 readiness[role]=dict(endpoint=proof['endpoint'],httpStatus=200,semanticStatus=proof['semanticStatus'],readinessPin=refs[0])
report['nativeSemanticReadiness']=readiness
history_custody=verify_installation_receipt_custody(HISTORY_RECEIPT_CUSTODY)
report['authorizedInstallationReceiptCustodyVerified']=True
report['installationReceiptCustody']=history_custody
report['originalProtectedHistoryFileCount']=len(protected_failure_pins)+1
report['verifiedDocumentPins']=len(verified)
'''
 script=script.replace('print(json.dumps(report))',insert+'\nprint(json.dumps(report))')
 request=json.loads((TASK/(restore_kind(suffix)+'-ui-submission.json')).read_text(encoding='utf-8'))['request']
 point=json.loads((TASK/'new-incremental-point-verified.json').read_text(encoding='utf-8'));protected,history_custody=custody_inputs(suffix)
 script=script.replace('REQUEST_LITERAL',repr(request)).replace('FULL_LITERAL',repr(point)).replace('PROTECTED_FAILURE_PINS_LITERAL',repr(protected))
 variables=dict(ROOT=('/mnt/intruoyi-data/' if suffix=='59' else '/var/lib/docker/intruoyi-data/')+'spug-main-restore-20261104-v3',TARGET='intruoyi-main-'+suffix+'-safe-restore-20261104-v1',INSTALL=allocator_installation(suffix),BASELINE=json.loads((TASK/('target-rollback-point-admission-'+restore_kind(suffix)+'.json')).read_text(encoding='utf8')))
 from common import allocator_contract_name
 variables['HEALTH_CONTRACT']=json.loads((TASK/allocator_contract_name(suffix)).read_text(encoding='utf8'))
 variables['HISTORY_RECEIPT_CUSTODY']=history_custody
 value=remote('172.30.30.'+suffix,'\n'.join(k+'='+repr(v) for k,v in variables.items())+'\n'+CUSTODY_SCRIPT+'\n'+script,120)
 write(TASK/('restore-'+suffix+'-native-evidence.json'),value);print(json.dumps(value))
