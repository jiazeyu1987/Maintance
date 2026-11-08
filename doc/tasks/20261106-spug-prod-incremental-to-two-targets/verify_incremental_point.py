"""Bind this new incremental's successful native result, parent and data proof."""
import json
from common import TASK,PRIVATE,active_source_installation,remote,write

SCRIPT=r'''
import ast,datetime,hashlib,json,pathlib,sys
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
verified=[]
def read(reference):
 assert 0<=reference['bytes']<=64*1024*1024,'METADATA_LIMIT'
 path=pathlib.Path(reference['path']);assert not path.is_symlink()
 raw=path.read_bytes();assert len(raw)==reference['bytes'] and hashlib.sha256(raw).hexdigest()==reference['sha256'],'PIN_CHANGED';verified.append(reference);return json.loads(raw)
matches=[]
for path in (root/'registry/points').glob('*.json'):
 reference=json.loads(path.read_bytes());value=read(reference)
 if value['reference']==OPERATION:matches.append(value)
assert len(matches)==1,'NEW_INCREMENTAL_NOT_PUBLISHED'
binding=matches[0];result=read(binding['resultPin'])
assert binding['sourceConfigRef']==SOURCE and result['operationId']==OPERATION and result['action']=='INCREMENTAL'
assert result['state']=='SUCCEEDED' and result['actualExitCode']==0 and result['failureCode'] is None
data=result['data'];manifest=read(data['manifestPin']);point=read(data['pointPin']);readback=read(data['readbackPin'])
parent=read(PARENT_PIN);parent_manifest=read(parent['manifestPin'])
assert parent['backupId']==PARENT and parent['pointType']=='FULL' and not parent['parentPointPins']
assert manifest['pointType']==point['pointType']=='INCREMENTAL' and manifest['parentPointPins']==point['parentPointPins']==[PARENT_PIN]
assert manifest['backupId']==point['backupId']==OPERATION and manifest['generationId']==point['generationId']==parent['generationId']
assert point['integrityState']=='COMPLETE' and point['rehearsalEligible'] is True
assert point['controlledRestoreEligible'] is False and point['blockedReason']=='REPOSITORY_RECOVERY_NOT_RUN'
assert point['manifestPin']==data['manifestPin']==readback['manifestPin'] and point['payloadRefs']==manifest['payloadRefs']==readback['payloadRefs']
assert readback['independentConnectionId'] and readback['schemaVersion']=='RepositoryMinimumReadback/v1' and readback['serverDurabilityVerified'] is False
assert 'payloadContentVerified' not in readback
assert point['readbackEvidencePin']==data['readbackPin']
capture_result=read(data['captureResultPin']);assert capture_result['state']=='SUCCEEDED' and capture_result['actualExitCode']==0
restoration=read(capture_result['data']['sourceRestorationPin']);assert restoration['restored'] is True and restoration['errors']==[]
close=read(point['ownerCloseEvidencePin']);terminal=read(point['originalExitEvidencePin'])
assert close['archiveReaderClosed'] is True and close['closeResponse']['state']=='ARCHIVE_READER_CLOSED_NOT_NAS_PROOF'
assert terminal['state']=='EXITED' and terminal['actualExitCode']==0 and terminal['processTerminated'] is True
recovery_binding=read(data['repositoryBindingPin']);assert recovery_binding['repositoryPointPin']==data['pointPin'] and recovery_binding['manifestPin']==data['manifestPin']
material=read(recovery_binding['recoveryMaterialPin']);database=material['database']
capture=read(database['capturePointPin']);parent_capture=read(next(p for p in parent['payloadRefs'] if p['path'].endswith('/payload/capture-content-point.json')))
assert capture['pointType']=='INCREMENTAL' and capture['parentRepositoryPointPin']==PARENT_PIN
assert capture['parentPointPin']['sha256']==next(p['sha256'] for p in parent['payloadRefs'] if p['path'].endswith('/payload/capture-content-point.json'))
assert database['method']=='BINLOG_SQL' and database['startPosition']==parent_capture['databaseEnd']==capture['databaseDelta']['parentPosition']
assert database['endPosition']==capture['databaseEnd'] and capture['databaseDelta']['kind']=='BINLOG_SQL' and capture['databaseDelta']['logMode']=='FILE_POSITION'
assert database['rawSqlPin'] and database['rawSqlPin']['bytes']>0 and database['sqlPin']['bytes']>0
scope_pin=next(p for p in point['payloadRefs'] if p['path'].endswith('/payload/database.sql.incremental-scope.json'))
scope=read(scope_pin);expected=read(database['expectedDataPin'])
engine=pathlib.Path(ENGINE);version=json.loads((engine/'package.json').read_bytes())
assert version['variant']=='standard' and version['fileVerification'] and version['payloadContentVerification']
assert version['packageSha256']==FILE_MANIFEST and len(version['files'])==127
assert all(hashlib.sha256((engine/name).read_bytes()).hexdigest()==sha for name,sha in version['files'].items())
sys.path[:0]=[str(engine/'common'),str(engine/'formal')]
from formal_data_evidence import incremental_observation_tables
changed=incremental_observation_tables(expected,scope,capture,expected['schema']['database'])
current_tables=sorted(name for name,kind in expected['schema']['catalog']['TABLES'] if kind!='VIEW')
assert '*' in changed,'EXPECTED_DATABASE_DDL_SCOPE_MISSING'
assert expected['affectedTables']==current_tables,'CURRENT_TABLE_DATA_NOT_ALL_OBSERVED'
assert material['recoveryPoint']==capture['commonRecoveryPoint']==point['commonRecoveryPoint']==manifest['commonRecoveryPoint']
objects=read(recovery_binding['objectContentIndexPin']);assert objects['parentExportIndexPin'] is not None and objects['repositoryBound'] is True
report=dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),operationId=OPERATION,state='SUCCEEDED',actualExitCode=0,finishedAt=result['finishedAt'],pointType='INCREMENTAL',generationId=point['generationId'],parentPointPins=point['parentPointPins'],parentBackupId=PARENT,manifestPin=data['manifestPin'],pointPin=data['pointPin'],recoveryMaterialPin=recovery_binding['recoveryMaterialPin'],commonRecoveryPoint=point['commonRecoveryPoint'],archivePath=str(pathlib.Path(data['manifestPin']['path']).parent.parent),payloadFiles=len(point['payloadRefs']),payloadBytes=sum(p['bytes'] for p in point['payloadRefs']),database=dict(method='BINLOG_SQL',startPosition=database['startPosition'],endPosition=database['endPosition'],compressedSqlBytes=database['sqlPin']['bytes'],rawSqlBytes=database['rawSqlPin']['bytes'],scopePin=scope_pin,scopePolicy=scope['policy'],segments=len(scope['segments']),eventCount=sum(s['eventCount'] for s in scope['segments']),rowEventCount=sum(s['rowEventCount'] for s in scope['segments']),ddlEventCount=sum(s['ddlEventCount'] for s in scope['segments']),expectedDataPin=database['expectedDataPin'],currentBaseTables=len(current_tables),allCurrentTableDataObserved=True),fileDelta=capture['fileDelta'],objectDelta=dict(changedContentCount=len(objects['changedContentSha256']),parentExportIndexPin=objects['parentExportIndexPin']),sourceStartCommandsCompleted=True,sourceIndependentHealthCheckRequired=True,verifiedMetadataPins=len(verified),registeredTargetAdmissionRequired=True,serverDurabilityVerified=False)
print(json.dumps(report))
'''
if __name__=='__main__':
 request=json.loads((TASK/'incremental-4-ui-submission.json').read_text(encoding='utf-8'))['request'];gate=json.loads((TASK/'incremental-4-preflight.json').read_text(encoding='utf-8'));engine=active_source_installation()
 variables=dict(OPERATION=request['operationId'],SOURCE=request['sourceConfigRef'],PARENT=request['parentChainRef'],PARENT_PIN=gate['parentPointPin'],ENGINE=engine['engine'],FILE_MANIFEST=engine['fileManifestSha256'])
 value=remote('172.30.30.57','\n'.join(k+'='+repr(v) for k,v in variables.items())+'\n'+SCRIPT,150)
 write(TASK/'new-incremental-point-verified.json',value);print(json.dumps(value))
