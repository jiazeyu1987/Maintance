"""Real bounded metadata and C1 input originals; no recovery authority is granted."""
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'ops/recovery'),str(ROOT/'ops/backup_engine/formal'),
    str(ROOT/'backend/src/main/resources')]
import recovery_preservation_source as consumer
from recovery_engine import RecoveryError
from repository_records import RepositoryError, canonical
from test_recovery_preservation_inputs import Inputs, inputs
from test_recovery_preservation_source import metadata, put
from test_recovery_preservation_source_publishers import derived, unchanged
from test_recovery_restore_inputs import sized_metadata


MIB=1024*1024
POLICY='preservation-policy58'
FLAGS=('payloadContentVerified','sourceAdmissionGranted','targetAdmitted','clearAuthorized')


@pytest.fixture
def tmp_path(tmp_path_factory):
    return tmp_path_factory.mktemp('pcs').resolve()


@pytest.fixture
def ordinary(unchanged):
    return Inputs(unchanged)


def begin(f):
    return consumer.PreservationCatalogueRead(f.control_pin,guard=lambda:None)


def ref(f):
    return f.request['recoveryPointRef']


def assert_account(value):
    pins=value['originalResultPins']
    assert len(pins)==len({p['path'] for p in pins})
    assert value['metadataBytes']==sum(p['bytes'] for p in pins)<=64*MIB


def pin_key(pin):
    return Path(pin['path']),pin['bytes'],pin['sha256']


def test_real_retained_control_and_paged_selection_keep_one_outer_finish(ordinary,monkeypatch):
    f=ordinary
    old_control=put(f.root/'config/prior-control.json',dict(f.control,preservationSourcePolicies={'retired':f.h['v2_pin']}))
    f.control_pin=put(Path(f.control_pin['path']),dict(f.control,retainedPreservationControlPins=[old_control]))
    actual_finish=consumer._Reads.finish; finished=[]
    def checked(reads):
        finished.append(reads);return actual_finish(reads)
    monkeypatch.setattr(consumer._Reads,'finish',checked)
    session=begin(f);resolved=session.control_resolution
    assert set(resolved)=={'schemaVersion','currentControlPin','publisherControlPins','originalResultPins','metadataBytes'}
    assert resolved['schemaVersion']=='PreservationControlPinsResolution/v1'
    assert resolved['currentControlPin']==f.control_pin and resolved['publisherControlPins']==[f.control_pin,old_control]
    assert_account(resolved)
    resolution_before=deepcopy(resolved)
    resolved['publisherControlPins'].clear();resolved['currentControlPin']['sha256']='0'*64
    assert session.control_resolution==resolution_before
    with pytest.raises(AttributeError):session.control_resolution={}
    page=session.page(POLICY);snapshot=page['snapshotDigest']
    assert page['schemaVersion']=='MainTargetPreservationPage/v1' and page['pageCount']==1
    assert page['points'][0]['reference']==ref(f) and page['complete'] is True
    assert page['payloadContentVerified'] is page['clearAuthorized'] is False
    assert set(map(pin_key,resolution_before['publisherControlPins']))<=set(map(pin_key,page['originalResultPins']))
    choice=session.select(POLICY,ref(f),snapshot_digest=snapshot)
    current=session.select_current(POLICY,ref(f))
    assert choice==current and choice['schemaVersion']=='MainTargetPreservationSelection/v1'
    assert choice['point']==page['points'][0] and choice['pointPin']==f.h['point_pin']
    assert all(choice[key] is False for key in FLAGS)
    assert finished==[]
    summary=session.finish()
    assert set(summary)=={'schemaVersion','controlResolution','metadataBytes','originalResultPins'}
    assert summary['schemaVersion']=='PreservationCatalogueReadSummary/v1'
    assert summary['controlResolution']==resolution_before and len(finished)==1
    assert summary['originalResultPins']==choice['originalResultPins']
    assert_account(summary)


def test_real_c1_verify_shares_same_account_and_never_reads_payload(inputs,monkeypatch):
    f=inputs.complete()
    actual=consumer._read_file; opened=[]
    payloads={f.h['payload'],*(f.root/'ordinary/archives').rglob('payload.bin')}
    def observe(path,maximum):
        assert path not in payloads,'CATALOGUE_SESSION_OPENED_PAYLOAD'
        opened.append(path)
        return actual(path,maximum)
    monkeypatch.setattr(consumer,'_read_file',observe)
    session=begin(f);choice=session.select_current(POLICY,ref(f))
    result=f.verify(publisher_control_pins=session.control_resolution['publisherControlPins'],
        reader=session.raw,fixed_reader=session.fixed)
    assert result['derivedOwner']==f.result
    assert all(result[key] is False for key in FLAGS)
    summary=session.finish();assert_account(summary)
    expected=[f.control_pin,f.h['point_pin'],f.base_pin,f.request_pin,*f.originals.values(),f.repository_binding,f.material]
    if 'a1' in f.h:expected += [f.h['a1'].base_pin,*f.h['a1'].originals.values()]
    assert set(map(pin_key,expected))<=set(map(pin_key,summary['originalResultPins']))
    assert set(p['path'] for p in choice['originalResultPins'])<set(p['path'] for p in summary['originalResultPins'])
    assert summary['metadataBytes']>choice['metadataBytes'] and opened


@pytest.mark.parametrize('extra',[0,1],ids=['exact-4MiB','4MiB-plus-one'])
@pytest.mark.parametrize('where',['current','retained'])
def test_control_document_retains_initial_four_mib_limit(ordinary,monkeypatch,extra,where):
    f=ordinary;selected=f.root/'config/large-control.json'
    large=sized_metadata(selected,4*MIB+extra,canonical(f.control))
    if where=='current':f.control_pin=large
    else:f.control_pin=put(Path(f.control_pin['path']),dict(f.control,retainedPreservationControlPins=[large]))
    actual=consumer._read_file;opened=[]
    def observe(path,maximum):
        opened.append(path);return actual(path,maximum)
    monkeypatch.setattr(consumer,'_read_file',observe)
    if extra:
        with pytest.raises(RepositoryError,match='PRESERVATION_SOURCE_METADATA_LIMIT'):begin(f)
        assert selected not in opened
    else:
        session=begin(f);assert large in session.control_resolution['publisherControlPins']
        assert selected in opened
        assert_account(session.finish())


@pytest.mark.parametrize('extra',[0,1],ids=['exact-64MiB','64MiB-plus-one'])
def test_fixed_body_uses_remaining_after_control_history_and_raw(ordinary,monkeypatch,extra):
    f=ordinary;session=begin(f);choice=session.select_current(POLICY,ref(f));assert_account(choice)
    remaining=64*MIB-choice['metadataBytes']
    assert 48*MIB<remaining<64*MIB
    for i in range(3):
        pin=sized_metadata(f.root/f'real-budget-{i}.json',16*MIB)
        assert len(session.raw(pin,16*MIB))==16*MIB
        if i==0:assert len(session.raw(pin,16*MIB))==16*MIB
    remaining-=48*MIB
    final_path=f.root/'shared-fixed-original.json';fixed=sized_metadata(final_path,remaining+extra)
    actual=consumer._read_file;opened=[]
    def observe(path,maximum):
        opened.append(path);return actual(path,maximum)
    monkeypatch.setattr(consumer,'_read_file',observe)
    if extra:
        with pytest.raises(RepositoryError,match='RESTORE_INPUTS_METADATA_LIMIT'):
            session.fixed(final_path,16*MIB)
        assert final_path not in opened
    else:
        assert session.fixed(final_path,16*MIB)==(fixed,{})
    summary=session.finish();assert_account(summary)
    assert summary['metadataBytes']==(64*MIB-remaining if extra else 64*MIB)
    assert (fixed in summary['originalResultPins']) is (extra==0)


@pytest.mark.parametrize('choice',['page','select','select_current'])
def test_first_policy_lock_rejects_switch_even_for_same_registered_pin(ordinary,choice):
    f=ordinary
    f.control_pin=put(Path(f.control_pin['path']),dict(f.control,preservationSourcePolicies={
        POLICY:f.h['v2_pin'],'second-registered-policy':f.h['v2_pin']}))
    session=begin(f);page=session.page(POLICY)
    with pytest.raises(RepositoryError,match='PRESERVATION_SOURCE_SESSION_POLICY_CHANGED'):
        if choice=='page':session.page('second-registered-policy')
        elif choice=='select':session.select('second-registered-policy',ref(f),snapshot_digest=page['snapshotDigest'])
        else:session.select_current('second-registered-policy',ref(f))


@pytest.mark.parametrize('change',['retained-only','invalid-map','unknown-ref'])
def test_only_current_control_policy_map_can_register_selection(ordinary,change):
    f=ordinary;control=deepcopy(f.control)
    if change=='retained-only':
        old=put(f.root/'config/previous-control.json',f.control)
        control.update(preservationSourcePolicies={},retainedPreservationControlPins=[old])
    elif change=='invalid-map':control['preservationSourcePolicies']=[f.h['v2_pin']]
    f.control_pin=put(Path(f.control_pin['path']),control)
    session=begin(f)
    with pytest.raises(RepositoryError,match='PRESERVATION_SOURCE_SESSION_POLICY_UNREGISTERED'):
        session.select_current('unknown' if change=='unknown-ref' else POLICY,ref(f))


@pytest.mark.parametrize('snapshot',[None,'0'*64],ids=['missing','wrong'])
def test_explicit_snapshot_is_still_required_for_strict_select(ordinary,snapshot):
    f=ordinary;session=begin(f)
    with pytest.raises(RepositoryError,match='CURSOR_INVALID' if snapshot is None else 'PRESERVATION_CATALOGUE_CHANGED_RESTART'):
        session.select(POLICY,ref(f),snapshot_digest=snapshot)


@pytest.mark.parametrize('kind',['control','hold-directory'])
def test_finish_detects_original_drift_and_closes_even_if_check_failed(ordinary,kind):
    f=ordinary;session=begin(f);session.select_current(POLICY,ref(f))
    if kind=='control':put(Path(f.control_pin['path']),dict(f.control,changed=True))
    else:(f.h['repository']/'.repository-control/preservation-holds'/'unexpected').write_bytes(b'{}')
    with pytest.raises(RepositoryError,match='METADATA_CHANGED|DIRECTORY_CHANGED'):session.finish()
    with pytest.raises(RepositoryError,match='PRESERVATION_SOURCE_SESSION_FINISHED'):session.finish()


@pytest.mark.parametrize('action',['raw','fixed','page','select','select_current','finish'])
def test_completed_session_refuses_all_further_reads_and_finish(ordinary,action):
    f=ordinary;session=begin(f);summary=session.finish();assert_account(summary)
    with pytest.raises(RepositoryError,match='PRESERVATION_SOURCE_SESSION_FINISHED'):
        if action=='raw':session.raw(f.control_pin,4*MIB)
        elif action=='fixed':session.fixed(Path(f.control_pin['path']),4*MIB)
        elif action=='page':session.page(POLICY)
        elif action=='select':session.select(POLICY,ref(f),snapshot_digest='0'*64)
        elif action=='select_current':session.select_current(POLICY,ref(f))
        else:session.finish()


def test_guard_and_invalid_retained_pin_fail_without_a_report(ordinary):
    f=ordinary
    def interrupted():raise RuntimeError('REQUEST_GUARD_EXPIRED')
    with pytest.raises(RuntimeError,match='REQUEST_GUARD_EXPIRED'):
        consumer.PreservationCatalogueRead(f.control_pin,guard=interrupted)
    bad=dict(f.control_pin,sha256='0'*64)
    current=put(f.root/'config/future.json',dict(f.control,retainedPreservationControlPins=[bad]))
    with pytest.raises((RepositoryError,RecoveryError),match='PIN_CHANGED|METADATA_CHANGED'):
        consumer.PreservationCatalogueRead(current,guard=lambda:None)
