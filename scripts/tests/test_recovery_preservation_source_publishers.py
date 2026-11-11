"""Real v2 publisher files; metadata protocols never prove a business restore.

The actual A1 resolver and controller metadata algorithm are used. The strict
preservation validator is never replaced with PASS. Linux full native history
remains a separate, explicitly scheduled verification.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'ops/recovery'),str(ROOT/'ops/backup_engine/formal'),
    str(ROOT/'backend/src/main/resources')]
from repository_records import RepositoryError,canonical
from recovery_engine import RecoveryError,digest
import recovery_preservation_source as consumer
from test_recovery_preservation_source import metadata,put,reference
from test_recovery_restore_inputs import Originals,sized_metadata


@pytest.fixture
def tmp_path(tmp_path_factory):
    return tmp_path_factory.mktemp('p').resolve()


def load(pin):
    return json.loads(Path(pin['path']).read_bytes())


def sync_history(h, *, owner=None, request=None, binding_changes=None, intent_changes=None):
    """Construct consistent protocol originals; do not alter a real audit record."""
    intent=load(h['intent_pin'])
    owner=owner or load(intent['configurationPin'])
    request=request or load(intent['requestPin'])
    intent['configurationPin']=put(Path(intent['configurationPin']['path']),owner)
    intent['requestPin']=put(Path(intent['requestPin']['path']),request)
    binding=load(h['binding_pin'])
    binding.update(configurationPin=intent['configurationPin'],requestPin=intent['requestPin'],
        policySha256=digest(owner['targetProgramPolicies']['target58']))
    binding.update(binding_changes or {})
    h['binding_pin']=put(Path(h['binding_pin']['path']),binding)
    intent['executionBindingPin']=h['binding_pin']
    intent.update(intent_changes or {})
    h['intent_pin']=put(Path(h['intent_pin']['path']),intent)
    hold_intent=load(h['hold_intent']);hold_intent['preservationIntentPin']=h['intent_pin']
    h['hold_intent']=put(Path(h['hold_intent']['path']),hold_intent)
    proof=load(h['proof_pin']);proof.update(intentPin=h['intent_pin'],holdIntentPin=h['hold_intent'])
    h['proof_pin']=put(Path(h['proof_pin']['path']),proof)
    hold_path=h['repository']/'.repository-control/preservation-holds'/('original_restore.json')
    hold=load(reference(hold_path));hold.update(intentPin=h['hold_intent'],archiveProofPin=h['proof_pin'])
    hold_pin=put(hold_path,hold)
    publication=Path(h['intent_pin']['path']).parent
    handoff_path=publication.parent/'session/handoff.json'
    handoff=load(reference(handoff_path));handoff['archiveProofPin']=h['proof_pin']
    handoff_pin=put(handoff_path,handoff)
    final_path=publication/'preservation.json';final=load(reference(final_path))
    final.update(intentPin=h['intent_pin'],archiveProofPin=h['proof_pin'],handoffPin=handoff_pin,holdPin=hold_pin)
    put(final_path,final)
    return h


def write_policy(h, rows):
    policy=deepcopy(h['policy'])
    policy.update(schemaVersion='MainTargetPreservationSourcePolicy/v2',publisherBindings=rows,
        maxDocumentBytes=16*1024*1024,maxMetadataBytes=64*1024*1024)
    h['v2_policy']=policy;h['v2_pin']=put(h['root']/'config/v2-source-policy.json',policy)
    return h['v2_pin']


@pytest.fixture
def unchanged(metadata):
    h=metadata
    h['owner']['targetProgramPolicies']={'target58':{'protocolOnly':'not a live program'}}
    h['owner_pin']=put(Path(h['owner_pin']['path']),h['owner'])
    h['policy']['publisherBindings'][0]['configurationPin']=h['owner_pin']
    h['policy_pin']=put(Path(h['policy_pin']['path']),h['policy'])
    h['build']()
    sync_history(h)
    h['row']=dict(kind='UNCHANGED_OWNER',configurationPin=h['owner_pin'],
        preservationPolicyPin=h['preservation_policy'])
    write_policy(h,[h['row']])
    return h


@pytest.fixture
def derived(metadata):
    h=metadata['build']()
    f=Originals(h['root']/'ordinary')
    f.owner.update(operationsRoot=h['owner']['operationsRoot'],targets=deepcopy(h['owner']['targets']),
        targetPreservationPolicies=deepcopy(h['owner']['targetPreservationPolicies']),
        targetProgramPolicies={'target58':{'protocolOnly':'not a live program'}})
    f.owner['targets']['target58']['typeSensitive']=1
    f.request.update(operationId='original_restore',targetConfigRef='target58')
    first=f.point('first');f.point('backup-new',[first]);f.controller_originals()
    sync_history(h,owner=f.derived,request=f.request)
    h['a1']=f
    h['row']=dict(kind='REQUEST_DERIVED_OWNER',baseConfigurationPin=f.base_pin,
        preservationPolicyPin=h['preservation_policy'],requestConfigurationsRoot=str(f.request_root),
        resolverContract='ArchiveRestoreOwner/v1')
    write_policy(h,[h['row']])
    return h


def listing(h):
    return consumer.list_preservation_points(h['v2_pin'],guard=lambda:None)


def test_v2_unchanged_owner_preserves_v1_rows_and_original_facts(unchanged):
    h=unchanged
    original={p:p.read_bytes() for p in h['root'].rglob('*') if p.is_file()}
    old=consumer.list_preservation_points(h['policy_pin'],guard=lambda:None)
    new=listing(h)
    assert new['points']==old['points']
    assert new['payloadContentVerified'] is new['clearAuthorized'] is False
    assert all(p.read_bytes()==raw for p,raw in original.items())


def test_v2_derived_owner_rebuilds_complete_a1_and_keeps_zero_payload_authority(derived,monkeypatch):
    h=derived;f=h['a1']
    payloads={h['payload'],*(f.root/'archives').rglob('payload.bin')}
    before={p:p.read_bytes() for p in h['root'].rglob('*') if p.is_file()}
    actual=consumer._read_file
    def bounded(path,*args,**kwargs):
        assert Path(path) not in payloads,'METADATA_PUBLISHER_READ_PAYLOAD'
        return actual(path,*args,**kwargs)
    monkeypatch.setattr(consumer,'_read_file',bounded)
    import recovery_restore_inputs as a1
    monkeypatch.setattr(a1,'_read_file',bounded)
    result=listing(h)
    row,=result['points']
    assert row['status']=='PRESERVATION_PUBLISHED' and row['sourceAdmissionAvailable'] is True
    assert row['restoreVerified'] is row['controlledRestoreEligible'] is row['sourceRestored'] is False
    assert result['payloadContentVerified'] is result['clearAuthorized'] is False
    for original in [f.base_pin,*f.originals.values(),*f.binding['evidencePins']]:
        assert any(Path(pin['path'])==Path(original['path']) and pin['bytes']==original['bytes'] and
            pin['sha256']==original['sha256'] for pin in result['originalResultPins'])
    assert all(p.read_bytes()==raw for p,raw in before.items())


@pytest.mark.parametrize('kind', ['wrong-base','wrong-request','recovery-nonsource','recovery-source',
    'operation-nonsource','operation-type','missing-inputs','missing-binding','wrong-root'])
def test_v2_derived_owner_rejects_incomplete_or_changed_originals(derived,kind):
    h=derived;f=h['a1'];expected=None
    if kind=='wrong-base':
        other=deepcopy(f.owner);other['deadlineMilliseconds']+=1
        h['row']['baseConfigurationPin']=f.write(f.root/'other-base.json',other)
        write_policy(h,[h['row']]);expected='RESTORE_INPUTS_ORIGINAL_BINDING_INVALID'
    elif kind=='wrong-request':
        changed=deepcopy(f.request);changed['recoveryPointRef']='another-point'
        sync_history(h,request=changed);expected='RESTORE_INPUTS_ORIGINAL_BINDING_INVALID'
    elif kind in ('recovery-nonsource','recovery-source'):
        changed=deepcopy(f.derived)
        if kind=='recovery-nonsource':changed['deadlineMilliseconds']+=1
        else:changed['sources']['source-A']['parentChains']={'injected':[]}
        f.replace_original('recoveryConfigurationPin',changed);expected='RESTORE_INPUTS_DERIVED_OWNER_CHANGED'
    elif kind.startswith('operation-'):
        changed=deepcopy(f.derived)
        if kind=='operation-type':changed['targets']['target58']['typeSensitive']=True
        else:changed['deadlineMilliseconds']+=1
        sync_history(h,owner=changed);expected='PRESERVATION_SOURCE_PUBLISHER_CHANGED'
    elif kind=='missing-inputs':Path(f.originals['requestInputsPin']['path']).unlink()
    elif kind=='missing-binding':Path(f.originals['pointBindingPin']['path']).unlink()
    else:
        root=h['root']/'empty-originals';root.mkdir()
        h['row']['requestConfigurationsRoot']=str(root);write_policy(h,[h['row']])
    with pytest.raises((RecoveryError,RepositoryError),match=expected or 'PRESERVATION_SOURCE_'):
        listing(h)


@pytest.mark.parametrize('change', ['configuration','request','context','reservation','program-digest'])
def test_v2_execution_binding_must_close_original_configuration_request_and_program(derived,change):
    h=derived
    field={'configuration':'configurationPin','request':'requestPin','context':'contextPin',
        'reservation':'reservationPin','program-digest':'policySha256'}[change]
    altered='b'*64 if change=='program-digest' else h['repository_pin']
    sync_history(h,binding_changes={field:altered})
    with pytest.raises(RepositoryError,match='PRESERVATION_SOURCE_BINDING_CHANGED'):
        listing(h)


@pytest.mark.parametrize('change', ['extra','missing-kind','unknown-kind','v1-tagged','unknown-resolver'])
def test_v2_tagged_union_is_exact_and_v1_does_not_infer_tags(derived,change):
    h=derived;row=deepcopy(h['row'])
    if change=='extra':row['configurationPin']=row['baseConfigurationPin']
    elif change=='missing-kind':row.pop('kind')
    elif change=='unknown-kind':row['kind']='TRUST_NAS_OWNER'
    elif change=='unknown-resolver':row['resolverContract']='AnyJsonPatch/v1'
    write_policy(h,[row])
    if change=='v1-tagged':
        h['v2_policy']['schemaVersion']='MainTargetPreservationSourcePolicy/v1'
        h['v2_pin']=put(Path(h['v2_pin']['path']),h['v2_policy'])
    expected='RESOLVER_UNSUPPORTED' if change=='unknown-resolver' else 'POLICY_INVALID'
    with pytest.raises(RepositoryError,match='PRESERVATION_SOURCE_'+expected):listing(h)


@pytest.mark.parametrize('mode', ['unchanged','derived'])
def test_v2_duplicate_publisher_is_rejected_before_history(request,mode):
    h=request.getfixturevalue(mode)
    write_policy(h,[h['row'],deepcopy(h['row'])])
    with pytest.raises(RepositoryError,match='PRESERVATION_SOURCE_PUBLISHER_DUPLICATE'):listing(h)


def test_v2_two_distinct_trust_paths_are_ambiguous_instead_of_first_match(derived):
    h=derived
    row=dict(kind='UNCHANGED_OWNER',configurationPin=put(h['root']/'trusted-derived.json',h['a1'].derived),
        preservationPolicyPin=h['preservation_policy'])
    write_policy(h,[h['row'],row])
    with pytest.raises(RepositoryError,match='PRESERVATION_SOURCE_PUBLISHER_AMBIGUOUS'):listing(h)


def test_v2_preservation_owner_resolver_is_explicitly_unsupported_without_a1(derived,monkeypatch):
    h=derived;h['row']['resolverContract']='PreservationRestoreOwner/v1';write_policy(h,[h['row']])
    import recovery_restore_inputs as a1
    def forbidden(*args,**kwargs):raise AssertionError('PRESERVATION_WAS_PASSED_TO_ORDINARY_A1')
    monkeypatch.setattr(a1,'verify_archive_restore_inputs',forbidden)
    with pytest.raises(RepositoryError,match='^PRESERVATION_SOURCE_RESOLVER_UNSUPPORTED$'):listing(h)


@pytest.mark.parametrize('extra',[0,1],ids=['exact-64MiB','64MiB-plus-one'])
def test_v2_nested_a1_and_outer_history_share_unique_raw_budget(derived,extra):
    h=derived
    baseline=listing(h)
    baseline_total=sum(pin['bytes'] for pin in baseline['originalResultPins'])
    assert baseline_total<1024*1024
    remaining=64*1024*1024-baseline_total+extra
    sizes=[16*1024*1024]*3+[remaining-48*1024*1024]
    assert 0<sizes[-1]<=16*1024*1024
    fillers=[sized_metadata(h['root']/('outer-budget-'+str(index)+'.json'),size)
        for index,size in enumerate(sizes)]
    reads=consumer._Reads(lambda:None)
    policy,repository=consumer._policy(reads,h['v2_pin'])
    for pin in fillers:
        reads.read(pin);reads.read(deepcopy(pin))
    if extra:
        with pytest.raises((RecoveryError,RepositoryError),match='METADATA_LIMIT'):
            consumer._catalogue(reads,policy,repository)
    else:
        rows,_=consumer._catalogue(reads,policy,repository)
        reads.finish();reads.finish()
        assert rows==baseline['points']
        assert sum(pin['bytes'] for pin in reads.pins())==64*1024*1024


def test_v2_nested_a1_reads_raw_original_bytes_and_rejects_pin_drift(derived):
    h=derived;f=h['a1']
    original=f.originals['pointBindingPin'];path=Path(original['path'])
    path.write_bytes(path.read_bytes()+b' \n\t')
    # The automatic fixed-path pin is valid, but raw noncanonical whitespace
    # must still be used; canonical re-encoding would break this positive case.
    f.originals['pointBindingPin']=reference(path)
    result=listing(h)
    assert any(pin['sha256']==f.originals['pointBindingPin']['sha256'] for pin in result['originalResultPins'])
    parent=f.binding['pointPin'];Path(parent['path']).write_bytes(b'{}')
    with pytest.raises((RecoveryError,RepositoryError),match='PIN_CHANGED|METADATA_CHANGED'):
        listing(h)
