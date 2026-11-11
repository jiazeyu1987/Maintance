"""Real metadata files only; these shaped inputs do not prove archive restore.

The complete producer closure is exercised separately on real Linux. No strict
validator result is replaced with a success envelope in this module.
"""
from copy import deepcopy
import hashlib
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'ops/recovery'), str(ROOT/'ops/backup_engine/formal')]
from repository_records import RepositoryError, canonical
from recovery_preservation_source import list_preservation_points, resolve_preservation_source


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(value)); path.chmod(0o600)
    return reference(path)


def reference(path):
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


@pytest.fixture
def metadata(tmp_path):
    """Small metadata protocol, deliberately NOT a complete native closure."""
    repo = tmp_path/'repository'; repo.mkdir()
    config = tmp_path/'config'; config.mkdir()
    identity = put(config/'identity.json', {'databaseUuid': 'original-target-identity'})
    repository = put(config/'repository.json', dict(schemaVersion='MainTargetPreservationRepository/v1',
        repositoryId='preservation-source', repositoryRoot=str(repo), sourceIdentityPin=identity,
        captureBinderPin=identity, readbackConfigPin=identity))
    preservation_policy = put(config/'preservation-policy.json',
        dict(schemaVersion='MainTargetPreservationPolicy/v1', targetConfigRef='target58',
            repositoryConfigurationPin=repository))
    owner = dict(operationsRoot=str(tmp_path/'operations'),
        targets={'target58': {'replacement': {'stateRoot': str(tmp_path/'claims')}}},
        targetPreservationPolicies={'target58': preservation_policy})
    owner_pin = put(config/'owner.json', owner)
    policy = dict(schemaVersion='MainTargetPreservationSourcePolicy/v1', sourceConfigRef='preserved58',
        originTargetConfigRef='target58', repositoryConfigurationPin=repository,
        publisherBindings=[dict(configurationPin=owner_pin, preservationPolicyPin=preservation_policy)],
        maxPoints=8, maxDocumentBytes=65536, maxMetadataBytes=2*1024*1024)
    state = dict(root=tmp_path, repository=repo, owner=owner, owner_pin=owner_pin,
        policy=policy, policy_pin=put(config/'source-policy.json', policy),
        repository_pin=repository, identity_pin=identity, preservation_policy=preservation_policy)

    def build(operation='original_restore', *, published=True, final=True, handoff=True,
              point_changes=None, manifest_changes=None, intent_changes=None):
        archive=repo/'preservations'/hashlib.sha256(operation.encode()).hexdigest()
        sidecar=archive/'.repository'; sidecar.mkdir(parents=True,exist_ok=True)
        publication=tmp_path/'operations'/operation/'target-preservation'/'publication'
        old_request=dict(schemaVersion='SmallAppBackupUiRequest/v1',operationId=operation,action='RESTORE',
            sourceConfigRef='old-source57',parentChainRef=None,recoveryPointRef='ordinary-full',targetConfigRef='target58')
        old_request_pin=put(tmp_path/'operations'/operation/'request.json',old_request)
        # Formal binding requires the original operation-local configuration.
        original_owner=put(tmp_path/'operations'/operation/'configuration.json',owner)
        binding_pin=put(tmp_path/'claims'/operation/'program-execution-binding.json',
            dict(schemaVersion='MainProgramExecutionBinding/v1',operationId=operation,targetConfigRef='target58',
                policySha256='a'*64,configurationPin=original_owner,requestPin=old_request_pin,
                reservationPin=identity,contextPin=identity))
        intent=dict(schemaVersion='MainTargetPreservationIntent/v1',operationId=operation,targetConfigRef='target58',
            role='TARGET_PRE_RESTORE',policyPin=preservation_policy,repositoryConfigurationPin=repository,
            configurationPin=original_owner,requestPin=old_request_pin,originalTargetPin=identity,
            captureConfigurationPin=identity,executionBindingPin=binding_pin,reservationPin=identity,
            contextPin=identity,readyEventPin=identity,replacingEventPin=identity,archivePath=str(archive),
            deadlineMonotonic=100.0,createdAt='2026-11-11T00:00:00Z')
        intent.update(intent_changes or {})
        intent_pin=put(publication/'intent.json',intent)
        holds=repo/'.repository-control'/'preservation-holds'
        hold_intent=put(holds/(operation+'-intent.json'),dict(schemaVersion='MainTargetPreservationHoldIntent/v1',
            repositoryId='preservation-source',operationId=operation,targetConfigRef='target58',role='TARGET_PRE_RESTORE',
            archivePath=str(archive),pointPath=str(sidecar/'preservation-point.json'),
            preservationIntentPin=intent_pin,createdAt='2026-11-11T00:00:00Z'))
        payload=archive/'payload'/'never-read.bin';payload.parent.mkdir();payload.write_bytes(b'not SQL; metadata protocol only')
        common=dict(backupId='captured-'+operation,generationId='original-generation',pointType='FULL',
            parentPointPins=[],commonRecoveryPoint='sha256:'+'c'*64,payloadRefs=[reference(payload)])
        manifest=dict(common,schemaVersion='RepositoryManifest/v1',sourceIdentityPin=identity,
            createdAt='2026-11-11T00:00:00Z',versionPins=[],toolPins=[],payloadTreePin=identity,copyProtectionPin=None)
        manifest.update(manifest_changes or {})
        manifest_pin=put(sidecar/'manifest.json',manifest)
        terminal_pin=put(sidecar/'capture-terminal.json',dict(schemaVersion='MainTargetCaptureTerminal/v1',
            operationId=operation,targetConfigRef='target58',materialsPin=identity,nativeEvidencePin=identity,
            sourceRestored=False,writersRemainQuiesced=True,finishedAt='2026-11-11T00:00:00Z'))
        point=dict(common,schemaVersion='MainTargetPreservationPoint/v1',role='TARGET_PRE_RESTORE',
            manifestPin=manifest_pin,readbackEvidencePin=identity,archiveCloseEvidencePin=identity,
            captureTerminalEvidencePin=terminal_pin,integrityState='COMPLETE',controlledRestoreEligible=False)
        point.update(point_changes or {})
        point_pin=put(sidecar/'preservation-point.json',point)
        proof=dict(schemaVersion='MainTargetPreservationArchive/v1',state='ARCHIVED_VERIFIED',operationId=operation,
            targetConfigRef='target58',role='TARGET_PRE_RESTORE',intentPin=intent_pin,materialsPin=identity,
            holdIntentPin=hold_intent,pointPin=point_pin,manifestPin=manifest_pin,payloadTreePin=identity,
            repositoryBindingPin=identity,recoveryMaterialPin=identity,objectContentIndexPin=identity,
            readbackPin=identity,sidecarReadbackPin=identity,archiveClosePin=identity,captureTerminalPin=terminal_pin,
            payloadContentVerified=True,serverDurabilityVerified=False,independentFailureDomain=False,
            originalResultPins=[],finishedAt='2026-11-11T00:00:00Z')
        proof_pin=put(publication/'archive-proof.json',proof)
        if published:
            hold_pin=put(holds/(operation+'.json'),dict(schemaVersion='MainTargetPreservationHold/v1',
                repositoryId='preservation-source',operationId=operation,targetConfigRef='target58',role='TARGET_PRE_RESTORE',
                intentPin=hold_intent,pointPin=point_pin,archiveProofPin=proof_pin,createdAt='2026-11-11T00:00:00Z'))
            handoff_pin=put(publication.parent/'session'/'handoff.json',dict(schemaVersion='MainTargetPreservationHandoff/v1',
                state='SUCCEEDED',operationId=operation,targetConfigRef='target58',archiveProofPin=proof_pin))
            final_pin=put(publication/'preservation.json',dict(schemaVersion='MainTargetPreservation/v1',
                state='SUCCEEDED',operationId=operation,targetConfigRef='target58',policyPin=preservation_policy,
                intentPin=intent_pin,archiveProofPin=proof_pin,handoffPin=handoff_pin,holdPin=hold_pin,
                originalResultPins=[],finishedAt='2026-11-11T00:00:00Z'))
            if not final:Path(final_pin['path']).unlink()
            if not handoff:Path(handoff_pin['path']).unlink()
        state.update(point_pin=point_pin,terminal_pin=terminal_pin,payload=payload,
            intent_pin=intent_pin,proof_pin=proof_pin,hold_intent=hold_intent,binding_pin=binding_pin,
            old_request_pin=old_request_pin,original_owner=original_owner)
        return state
    state['build']=build
    return state


@pytest.mark.parametrize('published,final,handoff,status,reason',[
    (False,False,False,'PRESERVATION_PENDING','PRESERVATION_SOURCE_PUBLICATION_PENDING'),
    (True,False,False,'PRESERVATION_BLOCKED','PRESERVATION_SOURCE_FINAL_MISSING'),
    (True,True,False,'PRESERVATION_BLOCKED','PRESERVATION_SOURCE_HANDOFF_MISSING'),
    (True,True,True,'PRESERVATION_PUBLISHED',None),
])
def test_metadata_only_states_preserve_original_facts(metadata,monkeypatch,published,final,handoff,status,reason):
    h=metadata['build'](published=published,final=final,handoff=handoff)
    original=Path.open;reads=[]
    def tracked(path,*args,**kwargs):
        assert Path(path)!=h['payload'],'PAYLOAD_OPENED_BY_METADATA_CATALOGUE'
        reads.append(str(path));return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'open',tracked)
    import recovery_preservation_source as consumer
    read_file=consumer._read_file
    def bounded(path,*args,**kwargs):
        assert Path(path)!=h['payload'],'PAYLOAD_READ_BY_METADATA_CATALOGUE'
        return read_file(path,*args,**kwargs)
    monkeypatch.setattr(consumer,'_read_file',bounded)
    before={str(p):p.read_bytes() for p in h['root'].rglob('*') if p.is_file() and p!=h['payload']}
    result=list_preservation_points(h['policy_pin'],guard=lambda:None)
    assert result['payloadContentVerified'] is result['clearAuthorized'] is False
    row,=result['points'];assert row['status']==status and row['blockedReason']==reason
    assert row['role']=='TARGET_PRE_RESTORE' and row['incrementalParentEligible'] is False
    if published:
        assert row['controlledRestoreEligible'] is row['sourceRestored'] is False
        assert row['writersRemainQuiesced'] is True
    else:
        assert row['controlledRestoreEligible'] is row['sourceRestored'] is row['writersRemainQuiesced'] is None
    assert row['restoreVerified'] is False and row['sourceAdmissionAvailable']==(reason is None)
    if published:assert row['pointPin']==h['point_pin']
    assert all(Path(path).read_bytes()==raw for path,raw in before.items())


@pytest.mark.parametrize('point_changes,manifest_changes,intent_changes',[
    ({'schemaVersion':'RepositoryPoint/v1'},None,None),
    ({'schemaVersion':'MainTargetPreservationPoint/v9'},None,None),
    ({'role':'SOURCE_BACKUP'},None,None),
    ({'controlledRestoreEligible':True},None,None),
    ({'controlledRestoreEligible':0},None,None),
    ({'pointType':'INCREMENTAL'},None,None),
    ({'parentPointPins':[{}]},None,None),
    (None,{'sourceIdentityPin':{'path':'/unknown','bytes':1,'sha256':'a'*64}},None),
    (None,None,{'targetConfigRef':'target57'}),
    (None,None,{'configurationPin':{'path':'/unknown','bytes':1,'sha256':'a'*64}}),
])
def test_metadata_rejects_wrong_typed_origin(metadata,point_changes,manifest_changes,intent_changes):
    h=metadata['build'](point_changes=point_changes,manifest_changes=manifest_changes,intent_changes=intent_changes)
    with pytest.raises(RepositoryError,match='PRESERVATION_SOURCE_'):
        list_preservation_points(h['policy_pin'],guard=lambda:None)


@pytest.mark.parametrize('change',[
    {'schemaVersion':'MainTargetPreservationSourcePolicy/v9'}, {'maxPoints':True}, {'maxPoints':0},
    {'maxDocumentBytes':0}, {'maxMetadataBytes':1}, {'publisherBindings':[]}, {'unknown':True},
])
def test_source_policy_is_explicit_and_bounded(metadata,change):
    h=metadata['build']();h['policy'].update(change)
    changed=put(h['root']/'config'/'changed-policy.json',h['policy'])
    with pytest.raises(RepositoryError,match='PRESERVATION_SOURCE_'):
        list_preservation_points(changed,guard=lambda:None)


def test_metadata_pin_drift_is_not_rehashed_away(metadata):
    h=metadata['build']();path=Path(h['point_pin']['path']);path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(RepositoryError,match='PRESERVATION_SOURCE_PIN_CHANGED'):
        list_preservation_points(h['policy_pin'],guard=lambda:None)


def test_metadata_guard_errors_propagate(metadata):
    h=metadata['build']()
    def guard():raise RuntimeError('DECLARED_GUARD_STOP')
    with pytest.raises(RuntimeError,match='DECLARED_GUARD_STOP'):
        list_preservation_points(h['policy_pin'],guard=guard)


def test_missing_or_unregistered_request_is_not_an_admission(metadata):
    h=metadata['build'](final=False)
    row,=list_preservation_points(h['policy_pin'],guard=lambda:None)['points']
    request=put(h['root']/'new-request.json',dict(schemaVersion='SmallAppBackupUiRequest/v1',operationId='new_restore',
        action='RESTORE',sourceConfigRef='preserved58',parentChainRef=None,recoveryPointRef=row['reference'],targetConfigRef='target59'))
    with pytest.raises(RepositoryError,match='PRESERVATION_SOURCE_FINAL_MISSING'):
        resolve_preservation_source(h['policy_pin'],request,guard=lambda:None)


def test_copied_hold_and_path_alias_are_rejected(metadata):
    h=metadata['build']();holds=h['repository']/'.repository-control'/'preservation-holds'
    put(holds/'copy.json',__import__('json').loads(Path(h['hold_intent']['path']).read_bytes()))
    with pytest.raises(RepositoryError,match='PRESERVATION_SOURCE_HOLD_'):
        list_preservation_points(h['policy_pin'],guard=lambda:None)


def test_unregistered_publisher_is_not_trusted_from_nas(metadata):
    h=metadata['build']()
    different=deepcopy(h['owner']);different['unapproved']='different publisher content'
    h['policy']['publisherBindings'][0]['configurationPin']=put(h['root']/'other-owner.json',different)
    changed=put(h['root']/'config'/'other-publisher.json',h['policy'])
    with pytest.raises(RepositoryError,match='PRESERVATION_SOURCE_PUBLISHER_UNTRUSTED'):
        list_preservation_points(changed,guard=lambda:None)


def test_directory_addition_at_final_guard_is_rejected(metadata):
    h=metadata['build']();added=[]
    def guard():
        if not added and (h['root']/'enable-race').exists():
            added.append(put(h['repository']/'.repository-control'/'preservation-holds'/'late.json',{}))
    import recovery_preservation_source as consumer
    original=consumer._Reads.finish
    def finishing(reader):
        (h['root']/'enable-race').touch();return original(reader)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(consumer._Reads,'finish',finishing)
        with pytest.raises(RepositoryError,match='PRESERVATION_SOURCE_DIRECTORY_CHANGED'):
            list_preservation_points(h['policy_pin'],guard=guard)


def test_one_deployment_policy_covers_multiple_operation_copies_without_per_point_registration(metadata):
    h=metadata['build']('restore_one');before=Path(h['policy_pin']['path']).read_bytes()
    h=metadata['build']('restore_two')
    result=list_preservation_points(h['policy_pin'],guard=lambda:None)
    assert len(result['points'])==2 and all(row['sourceAdmissionAvailable'] for row in result['points'])
    assert Path(h['policy_pin']['path']).read_bytes()==before
    assert {row['operationId'] for row in result['points']}=={'restore_one','restore_two'}


def test_duplicate_captured_identity_is_rejected(metadata):
    h=metadata['build']('restore_one')
    metadata['build']('restore_two',point_changes={'backupId':'captured-restore_one'},
        manifest_changes={'backupId':'captured-restore_one'})
    with pytest.raises(RepositoryError,match='PRESERVATION_SOURCE_POINT_DUPLICATE'):
        list_preservation_points(h['policy_pin'],guard=lambda:None)


@pytest.mark.parametrize('field', ['manifestPin','captureTerminalEvidencePin'])
def test_metadata_never_opens_payload_disguised_as_sidecar(metadata,monkeypatch,field):
    h=metadata['build']()
    point=__import__('json').loads(Path(h['point_pin']['path']).read_bytes())
    point[field]=reference(h['payload']);changed=put(Path(h['point_pin']['path']),point)
    hold_path=h['repository']/'.repository-control'/'preservation-holds'/'original_restore.json'
    hold=__import__('json').loads(hold_path.read_bytes());hold['pointPin']=changed;put(hold_path,hold)
    proof=__import__('json').loads(Path(h['proof_pin']['path']).read_bytes());proof['pointPin']=changed
    proof_pin=put(Path(h['proof_pin']['path']),proof)
    hold['archiveProofPin']=proof_pin;put(hold_path,hold)
    import recovery_preservation_source as consumer
    original=consumer._read_file
    def bounded(path,*args,**kwargs):
        assert Path(path)!=h['payload'],'PAYLOAD_OPENED_BEFORE_SIDECAR_PATH_REJECTION'
        return original(path,*args,**kwargs)
    monkeypatch.setattr(consumer,'_read_file',bounded)
    with pytest.raises(RepositoryError,match='PRESERVATION_SOURCE_'):
        list_preservation_points(h['policy_pin'],guard=lambda:None)


@pytest.mark.parametrize('missing,reason',[
    ('point','PRESERVATION_SOURCE_POINT_MISSING'),
    ('proof','PRESERVATION_SOURCE_ARCHIVE_PROOF_MISSING'),
    ('manifest','PRESERVATION_SOURCE_MANIFEST_MISSING'),
    ('terminal','PRESERVATION_SOURCE_CAPTURE_TERMINAL_MISSING'),
])
def test_missing_sidecar_remains_visible_but_cannot_be_admitted(metadata,missing,reason):
    h=metadata['build']()
    point=__import__('json').loads(Path(h['point_pin']['path']).read_bytes())
    selected={'point':h['point_pin'],'proof':h['proof_pin'],
        'manifest':point['manifestPin'],'terminal':point['captureTerminalEvidencePin']}[missing]
    Path(selected['path']).unlink()
    result=list_preservation_points(h['policy_pin'],guard=lambda:None)
    row,=result['points']
    assert row['status']=='PRESERVATION_BLOCKED' and row['blockedReason']==reason
    assert row['pointPin']==h['point_pin'] and row['reference']
    assert row['sourceAdmissionAvailable'] is row['restoreVerified'] is False
    assert result['clearAuthorized'] is result['payloadContentVerified'] is False


def test_main_sized_point_and_manifest_over_four_mib_are_metadata_only(metadata,monkeypatch):
    """Real >4MiB JSON/pins; declared payloads remain deliberately unverified.

    No native/readback success is claimed for this metadata-only protocol. The
    separate Linux test supplies the genuine complete preservation closure.
    """
    import json
    h=metadata['build']()
    point=json.loads(Path(h['point_pin']['path']).read_bytes())
    manifest=json.loads(Path(point['manifestPin']['path']).read_bytes())
    original_payload=reference(h['payload'])
    payloads=[dict(original_payload,path=str(h['payload'].parent/(str(i).zfill(5)+'-'+'p'*200)))
        for i in range(14339)]
    manifest['payloadRefs']=payloads
    manifest_pin=put(Path(point['manifestPin']['path']),manifest)
    point.update(payloadRefs=payloads,manifestPin=manifest_pin)
    point_pin=put(Path(h['point_pin']['path']),point)
    assert manifest_pin['bytes']>4*1024*1024 and point_pin['bytes']>4*1024*1024
    proof=json.loads(Path(h['proof_pin']['path']).read_bytes())
    proof.update(pointPin=point_pin,manifestPin=manifest_pin)
    proof_pin=put(Path(h['proof_pin']['path']),proof)
    hold_path=h['repository']/'.repository-control'/'preservation-holds'/'original_restore.json'
    hold=json.loads(hold_path.read_bytes());hold.update(pointPin=point_pin,archiveProofPin=proof_pin)
    hold_pin=put(hold_path,hold)
    publication=Path(h['intent_pin']['path']).parent
    final=json.loads((publication/'preservation.json').read_bytes())
    handoff=json.loads(Path(final['handoffPin']['path']).read_bytes());handoff['archiveProofPin']=proof_pin
    final.update(archiveProofPin=proof_pin,holdPin=hold_pin,handoffPin=put(Path(final['handoffPin']['path']),handoff))
    put(publication/'preservation.json',final)
    h['policy'].update(maxDocumentBytes=16*1024*1024,maxMetadataBytes=64*1024*1024)
    policy_pin=put(h['root']/'config'/'large-source-policy.json',h['policy'])
    import recovery_preservation_source as consumer
    original=consumer._read_file;opened=[]
    def metadata_only(path,*args,**kwargs):
        actual=Path(path)
        assert actual!=h['payload'] and h['payload'].parent not in actual.parents,'PAYLOAD_OPENED_FOR_LARGE_METADATA'
        opened.append(actual);return original(path,*args,**kwargs)
    monkeypatch.setattr(consumer,'_read_file',metadata_only)
    result=list_preservation_points(policy_pin,guard=lambda:None)
    row,=result['points']
    assert row['status']=='PRESERVATION_PUBLISHED' and row['pointPin']==point_pin
    assert row['controlledRestoreEligible'] is row['restoreVerified'] is False
    assert result['payloadContentVerified'] is result['clearAuthorized'] is False
    assert Path(point_pin['path']) in opened and Path(manifest_pin['path']) in opened
    print('ACTUAL_MAIN_METADATA_BYTES point='+str(point_pin['bytes'])+' manifest='+str(manifest_pin['bytes']))
