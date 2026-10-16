"""Local admission/expiry checks; no services, restore or VERIFIED output is simulated."""
from pathlib import Path
from datetime import datetime
import json
import subprocess
import sys
from types import SimpleNamespace

import pytest

RECOVERY = Path(__file__).resolve().parents[2]/'ops/recovery'
sys.path.insert(0, str(RECOVERY))
from recovery_engine import RecoveryError, load, pin, write
from recovery_data_derived import restored_inputs
from recovery_data_redis_sessions import (EXECUTOR_KEY, FIELDS, archived_expiries, database_result,
                                         expiry_observation, original_expiry,
                                         registration, request_contract, session_provenance, target_configuration)


def request():
    result = dict.fromkeys(FIELDS)
    result.update(schemaVersion='RecoveryDerivedRequest/v1', operationId='local-admission',
                  requestId='local-admission-redis', action='DERIVED_REBUILD', className='redis',
                  inputPins=[], rebuildFromPin={'unresolved': True}, deadlineMilliseconds=1000)
    return result


@pytest.mark.parametrize('field,value', [('action','DERIVED_RESTORE'),('className','queue'),
                                       ('inputPins',[{}]),('rebuildFromPin',None)])
def test_other_actions_payloads_and_missing_database_are_rejected(field, value):
    value_request = request(); value_request[field] = value
    with pytest.raises(RecoveryError, match='REDIS_DERIVED_REQUEST_INVALID'): request_contract(value_request)


def test_extra_wire_fields_are_rejected():
    value = request(); value['objectResultPin'] = {}
    with pytest.raises(RecoveryError, match='REDIS_DERIVED_REQUEST_INVALID'): request_contract(value)


def test_missing_existing_registry_entry_fails_without_loading_business_modules():
    with pytest.raises(RecoveryError, match='DERIVED_EXECUTOR_NOT_REGISTERED'):
        registration({'derivedAdapters':{}}, {})


def test_candidate_script_hash_does_not_approve_itself():
    ref = pin(RECOVERY/'recovery_data_redis_sessions.py')
    policy = {'derivedAdapters': {EXECUTOR_KEY:{'className':'redis','classification':'REBUILD','scriptPin':ref}},
              'moduleSourcePins':[ref]}
    with pytest.raises(RecoveryError, match='DERIVED_EXECUTOR_NOT_APPROVED'):
        registration(policy, {'derivedExecutorSha256s':[]})


@pytest.mark.parametrize('ttl',[1001, -1, -2, True])
def test_cache_must_not_extend_original_expiry_or_lose_ttl(ttl):
    with pytest.raises(RecoveryError): original_expiry(2000, b'value', ttl, 1000, 1005)


def test_elapsed_time_window_preserves_absolute_expiry():
    assert original_expiry(2000, b'value', 998, 1000, 1005)
    with pytest.raises(RecoveryError, match='REDIS_ORIGINAL_EXPIRY_NOT_PRESERVED'):
        original_expiry(2000, b'value', 994, 1000, 1005)


def test_natural_expiry_is_excluded_and_clock_reversal_is_rejected():
    assert not original_expiry(1003, None, -2, 1000, 1005)
    with pytest.raises(RecoveryError, match='REDIS_EXPIRY_READBACK_INVALID'):
        original_expiry(2000, b'value', 999, 1005, 1000)


def expiry_projection():
    """Scalar unit inputs only, never inserted into SQL or a running service."""
    original={'table':'smallapp_sessions','tenant_id':'122','user_id':'1',
              'expires_at':'2026-10-14 10:00:00.123456'}
    reference={'schemaVersion':'RecoveryReferenceInventory/v1','complete':True,
               'recoveryPoint':'point-i1','databaseRows':[original]}
    restored={'tenant_id':122,'user_id':1,'expires_at':datetime(2026,10,14,10,0,0,123456)}
    return reference,restored


def test_archived_expiry_matches_exact_microseconds_without_exposing_identity():
    reference,restored=expiry_projection()
    matches=archived_expiries(reference,'point-i1',[restored])
    assert matches==[{'referenceRowIndex':0,'originalSqlExpiresAtUtc':'2026-10-14T10:00:00.123456Z',
                     'originalSqlExpiryUtcMilliseconds':1791972000123}]
    restored['expires_at']=restored['expires_at'].replace(microsecond=123457)
    with pytest.raises(RecoveryError,match='REDIS_ARCHIVED_SQL_EXPIRY_MISMATCH'):
        archived_expiries(reference,'point-i1',[restored])


def test_archived_expiry_duplicates_preserve_occurrences_and_missing_rows_fail():
    reference,restored=expiry_projection()
    reference['databaseRows'].append(dict(reference['databaseRows'][0]))
    matches=archived_expiries(reference,'point-i1',[restored,dict(restored)])
    assert [row['referenceRowIndex'] for row in matches]==[0,1]
    with pytest.raises(RecoveryError,match='REDIS_ARCHIVED_SESSION_COUNT_MISMATCH'):
        archived_expiries(reference,'point-i1',[restored])


@pytest.mark.parametrize('field,value',[('recoveryPoint','point-full'),('complete',False)])
def test_wrong_or_incomplete_archived_expiry_inventory_fails(field,value):
    reference,restored=expiry_projection();reference[field]=value
    with pytest.raises(RecoveryError,match='REDIS_ARCHIVED_SESSION_INVENTORY_REQUIRED'):
        archived_expiries(reference,'point-i1',[restored])


def test_archived_session_secret_fields_are_not_admitted():
    reference,restored=expiry_projection();reference['databaseRows'][0]['session_hash']='private'
    with pytest.raises(RecoveryError,match='REDIS_ARCHIVED_SESSION_ROW_INVALID'):
        archived_expiries(reference,'point-i1',[restored])


def expiry_match():
    return {'referenceRowIndex':0,'originalSqlExpiresAtUtc':'1970-01-01T00:00:02.000000Z',
            'originalSqlExpiryUtcMilliseconds':2000}


def test_exact_cache_expiry_observation_keeps_measured_fields_and_no_payload():
    result=expiry_observation(expiry_match(),2000,b'private-cache-payload',998,2000,1000,1005)
    assert result['cacheExpiryUtcMilliseconds']==2000 and result['observedAtUtcMilliseconds']==1005
    assert result['accepted'] is True and result['decision']=='LIVE_ACCEPTED'
    assert 'private-cache-payload' not in json.dumps(result)
    assert all(key not in result for key in ('session_hash','cookie','csrf','credential','raw'))


@pytest.mark.parametrize('cache_expiry',[2001,1999,-1,-2,True])
def test_missing_or_changed_actual_absolute_expiry_cannot_be_accepted(cache_expiry):
    with pytest.raises(RecoveryError):
        expiry_observation(expiry_match(),2000,b'private-cache-payload',998,cache_expiry,1000,1005)


def test_expired_absence_needs_real_negative_get_ttl_and_absolute_expiry():
    result=expiry_observation(expiry_match(),2000,None,-2,-2,2001,2005)
    assert result['accepted'] is False and result['cacheExpiryUtcMilliseconds'] is None
    assert result['decision']=='EXPIRED_ABSENT' and result['redisExpireTimeMilliseconds']==-2
    with pytest.raises(RecoveryError,match='REDIS_EXPIRED_SESSION_REVIVED'):
        expiry_observation(expiry_match(),2000,b'revived',1000,3000,2001,2005)


def test_matching_ttl_cannot_mask_changed_archived_sql_expiry():
    match=expiry_match();match['originalSqlExpiryUtcMilliseconds']=1999
    with pytest.raises(RecoveryError,match='REDIS_ABSOLUTE_EXPIRY_READBACK_INVALID'):
        expiry_observation(match,2000,b'private-cache-payload',998,2000,1000,1005)


def test_expiry_observation_matches_actual_w06_pure_consumer_without_ui_execution():
    live=expiry_observation(expiry_match(),2000,b'private-cache-payload',998,2000,1000,1005)
    expired=expiry_observation(expiry_match(),2000,None,-2,-2,2001,2005)
    fields={'rows':'/rows','originalExpiry':'/originalSqlExpiryUtcMilliseconds',
            'restoredExpiry':'/restoredSqlExpiryUtcMilliseconds','observedAt':'/observedAtUtcMilliseconds',
            'cacheExpiry':'/cacheExpiryUtcMilliseconds','accepted':'/accepted'}
    consumer=RECOVERY.parents[1]/'doc/tasks/20261010-recovery-verification-dev/smallapp-spug-20261014/browser-rehearsal.cjs'
    script="""const {expiryReadback}=require(process.argv[1]);
const input=JSON.parse(process.argv[2]);
const result=expiryReadback(input.data,input.fields);
let rejected=false;
try { expiryReadback({rows:[],liveRowsRead:1,originalAbsoluteExpiryVerified:true},input.fields); }
catch (error) { if(error.safeCode!=='ORIGINAL_SESSION_EXPIRY_READBACK_REQUIRED') throw error; rejected=true; }
if(!rejected) throw new Error('AGGREGATE_WAS_ACCEPTED');
process.stdout.write(JSON.stringify(result));"""
    process=subprocess.run(['node','-e',script,str(consumer),json.dumps({'data':{'rows':[live,expired]},
                                                                      'fields':fields})],capture_output=True)
    assert process.returncode==0 and process.stderr==b''
    result=json.loads(process.stdout)
    assert result['sessionCount']==2 and result['liveCount']==result['expiredCount']==1
    assert result['absoluteExpiryReadbackVerified'] is True
    assert result['naturalExpiryBrowserDenialVerified'] is False


@pytest.mark.parametrize('source_uuid,target_uuid',[('other-source','target-db'),('source-db','source-db')])
def test_expiry_provenance_rejects_wrong_original_or_target_database_before_comparison(tmp_path,source_uuid,target_uuid):
    reference=write(tmp_path/'reference.json',{'databaseRows':[]})
    expected=write(tmp_path/'expected.json',{'observationIdentity':{'databaseUuid':source_uuid}})
    observed=write(tmp_path/'observed.json',{'observationIdentity':{'databaseUuid':target_uuid}})
    database=write(tmp_path/'database.json',{'observedPin':observed})
    native=SimpleNamespace(material={'referenceInventoryPin':reference,'database':{'expectedDataPin':expected},
                                    'payloadPins':[reference,expected],'sourceDatabaseUuid':'source-db'},
                           db_uuid='target-db',modules={})
    with pytest.raises(RecoveryError,match='REDIS_SESSION_DATABASE_PROVENANCE_MISMATCH'):
        session_provenance(native,{'rebuildFromPin':database})


def restored_records(tmp_path):
    observed = write(tmp_path/'observed.json', {'localAdmissionBytes':True})
    comparison = write(tmp_path/'comparison.json', {'localAdmissionBytes':True})
    mapping = write(tmp_path/'mapping.json', {'localAdmissionBytes':True})
    position = {'file':'mysql-bin.000002','position':128}
    database = dict(recoveryPoint='point-i1',databaseUuid='target-db',endPosition=position,
                    fullSchemaDataEquivalenceVerified=True, observedPin=observed,comparisonPin=comparison)
    objects = dict(recoveryPoint='point-i1',versionMappingPin=mapping)
    material = {'recoveryPoint':'point-i1','database':{'endPosition':position}}
    return database, objects, material


@pytest.mark.parametrize('field,value',[('recoveryPoint','other-point'),('databaseUuid','source-db'),
                                      ('fullSchemaDataEquivalenceVerified',False),
                                      ('endPosition',{'file':'mysql-bin.000002','position':129})])
def test_rebuild_from_wrong_database_result_is_rejected(tmp_path, field, value):
    database, _, material = restored_records(tmp_path); database[field] = value
    derived = {'rebuildFromPin':write(tmp_path/'database.json', database),'recoveryPoint':'point-i1'}
    with pytest.raises(RecoveryError, match='REDIS_RESTORED_DATABASE_REQUIRED'):
        database_result(derived, material, 'target-db')


def test_derived_stage_rejects_object_point_mismatch(tmp_path):
    database, objects, material = restored_records(tmp_path); objects['recoveryPoint']='point-full'
    native = SimpleNamespace(request={'databaseResultPin':write(tmp_path/'database.json',database),
                                     'objectResultPin':write(tmp_path/'objects.json',objects)},
                             plan={'recoveryPoint':'point-i1'},material=material,db_uuid='target-db')
    with pytest.raises(RecoveryError, match='DERIVED_RESTORED_INPUTS_REQUIRED'): restored_inputs(native)


def test_derived_stage_rejects_changed_object_mapping_before_dispatch(tmp_path):
    database, objects, material = restored_records(tmp_path)
    native = SimpleNamespace(request={'databaseResultPin':write(tmp_path/'database.json',database),
                                     'objectResultPin':write(tmp_path/'objects.json',objects)},
                             plan={'recoveryPoint':'point-i1'},material=material,db_uuid='target-db')
    Path(objects['versionMappingPin']['path']).write_bytes(b'changed object mapping')
    with pytest.raises(RecoveryError, match='PIN_CHANGED'): restored_inputs(native)


def configuration_case(tmp_path):
    endpoints = {'database':{'host':'mysql','port':3306}, 'redis':{'host':'redis','port':6379},
                 'objectStore':{'host':'minio','port':9000}}
    native = SimpleNamespace(config={'database':'target-db','imagePins':['r2-images'],
                                     'buckets':['task-bucket'],
                                     'configurationPin':write(tmp_path/'config.json',{'endpointMap':endpoints})},
                             config_services={'mysql':{'ip':'172.31.1.2'},'minio':{'ip':'172.31.1.3'},
                                              'redis':{'ip':'172.31.1.4','name':'target-redis'}})
    settings = {'version':'r2','runtimeRole':'TARGET','startState':'PROTECTED','tenantId':122,
                'username':'aoteman','database':{'name':'target-db','host':'mysql','port':3306},
                'redis':{'database':0,'host':'redis','port':6379,'instanceId':'target-redis'},
                's3':{'endpoint':'http://minio:9000','bucket':'task-bucket'}}
    adapter = {'version':'r2','imagePins':['r2-images']}
    return settings, native, adapter


@pytest.mark.parametrize('changes',[{'runtimeRole':'SOURCE'},{'startState':'OPEN'},{'tenantId':1},
                                    {'version':'r1'}])
def test_source_open_other_tenant_and_old_version_are_rejected(tmp_path, changes):
    settings, native, adapter = configuration_case(tmp_path); settings.update(changes)
    with pytest.raises(RecoveryError, match='REDIS_APPLICATION_TARGET_BINDING_INVALID'):
        target_configuration(settings,native,adapter)


def test_arbitrary_redis_address_and_shared_db_are_rejected(tmp_path):
    settings, native, adapter = configuration_case(tmp_path)
    settings['redis']['host']='source-redis'
    with pytest.raises(RecoveryError, match='REDIS_APPLICATION_ENDPOINT_MISMATCH'):
        target_configuration(settings,native,adapter)
    settings['redis']['host']='redis'; settings['redis']['database']=1
    with pytest.raises(RecoveryError, match='REDIS_APPLICATION_TARGET_BINDING_INVALID'):
        target_configuration(settings,native,adapter)


def test_child_invalid_action_has_original_failure_and_no_verified_data(tmp_path):
    value=request();value['action']='DERIVED_RESTORE'
    input_ref=write(tmp_path/'request.json',value); output=tmp_path/'result.json'
    process=subprocess.run([sys.executable,str(RECOVERY/'recovery_data_redis_sessions.py'),
                            '--request',input_ref['path'],'--output',str(output)],capture_output=True)
    assert process.returncode==1 and process.stdout==b'' and process.stderr==b''
    result=load(output)
    assert result['state']=='FAILED_RETAINED' and result['data'] is None
    assert result['failureCode']=='REDIS_DERIVED_REQUEST_INVALID' and result['originalResultPins']==[]
