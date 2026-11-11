"""Fixed-point metadata borrowing the real caller meter, never admission."""
from copy import deepcopy
import hashlib
from pathlib import Path

import pytest

from test_recovery_preservation_source import metadata,put,reference
from test_recovery_preservation_source_publishers import unchanged,derived,load,write_policy
from test_recovery_restore_inputs import sized_metadata
from repository_records import RepositoryError,canonical
import recovery_preservation_source as consumer


class BorrowedReads:
    """Actual existing ledger, exposing only the agreed caller protocol."""
    def __init__(self):
        self.actual=consumer._Reads(lambda:None)
        self.opened=[]
        self.guard=self.actual.guard

    @property
    def maximum(self):return self.actual.maximum
    @maximum.setter
    def maximum(self,value):self.actual.maximum=value
    @property
    def total_limit(self):return self.actual.total_limit
    @total_limit.setter
    def total_limit(self,value):self.actual.total_limit=value
    @property
    def total(self):return self.actual.total

    def read(self,pin):
        self.opened.append(Path(pin['path']))
        return self.actual.read(pin)
    def fixed(self,path):
        self.opened.append(Path(path))
        return self.actual.fixed(path)
    def raw(self,pin,maximum):
        self.opened.append(Path(pin['path']))
        return self.actual.raw(pin,maximum)
    def directory(self,path):return self.actual.directory(path)
    def optional(self,path):return self.actual.optional(path)
    def budget(self,condition):return self.actual.budget(condition)
    def pins(self):return self.actual.pins()
    def finish(self):raise AssertionError('HELPER_FINISHED_CALLER_LEDGER')


def inputs(h):
    old=load(h['intent_pin'])['operationId']
    ref='preservation-'+hashlib.sha256(canonical(h['point_pin'])).hexdigest()
    request=dict(schemaVersion='SmallAppBackupUiRequest/v1',operationId='bound_new_restore',action='RESTORE',
        sourceConfigRef=h['v2_policy']['sourceConfigRef'],parentChainRef=None,recoveryPointRef=ref,targetConfigRef='target59')
    control_pin=put(h['root']/'caller-control-only.json',{'C1MustVerifyThisControl':'not an authority claim'})
    binding=dict(schemaVersion='SmallAppPreservationPointBinding/v1',reference=ref,
        sourceConfigRef=request['sourceConfigRef'],sourcePolicyPin=h['v2_pin'],pointPin=h['point_pin'],
        publicationOperationId=old,controlConfigurationPin=control_pin)
    return request,binding


def describe(h,request,binding,reads=None):
    reads=reads or BorrowedReads()
    return consumer._describe_bound_preservation(reads,h['v2_pin'],request,binding)


@pytest.mark.parametrize('publisher',['unchanged','derived'])
def test_fixed_description_reuses_original_row_and_real_shared_reads_without_enumeration(request,publisher,monkeypatch):
    h=request.getfixturevalue(publisher);new,binding=inputs(h);reads=BorrowedReads()
    actual_policy,actual_repository=consumer._policy(reads.actual,h['v2_pin'])
    intent_pin,intent=reads.actual.fixed(h['hold_intent']['path'])
    hold_path=h['repository']/'.repository-control/preservation-holds'/('original_restore.json')
    final=reads.actual.fixed(hold_path)
    expected_row,expected_history=consumer._row(reads.actual,actual_policy,actual_repository,
        binding['publicationOperationId'],intent_pin,intent,final)
    baseline=reads.total
    # An unrelated malformed new hold must not force a directory scan/restart.
    (hold_path.parent/'unrelated-invalid.json').write_bytes(b'not JSON')
    def forbidden(*args,**kwargs):raise AssertionError('HELPER_CREATED_NEW_LEDGER')
    monkeypatch.setattr(consumer,'_Reads',forbidden)
    policy,repository,row,history=describe(h,new,binding,reads)
    assert policy==actual_policy and repository==actual_repository
    assert row==expected_row and history==expected_history
    assert row['status']=='PRESERVATION_PUBLISHED' and row['blockedReason'] is None
    assert row['controlledRestoreEligible'] is row['sourceRestored'] is row['restoreVerified'] is False
    assert row['writersRemainQuiesced'] is True
    assert reads.total==baseline and reads.total==sum(pin['bytes'] for pin in reads.pins())
    assert h['payload'] not in reads.opened and Path(binding['controlConfigurationPin']['path']) not in reads.opened
    assert {path.name for path in reads.opened if path.parent==hold_path.parent}=={'original_restore-intent.json','original_restore.json'}
    if publisher=='derived':
        assert all(any(Path(pin['path'])==Path(original['path']) and pin['sha256']==original['sha256']
            for pin in reads.pins()) for original in h['a1'].originals.values())
    reads.actual.finish()


@pytest.mark.parametrize('change',['extra','schema','source','reference','policy','point-pin','control-pin','old-operation'])
def test_exact_binding_shape_and_current_request_mismatch_are_rejected(unchanged,change):
    h=unchanged;request,binding=inputs(h)
    if change=='extra':binding['admitted']=True
    elif change=='schema':binding['schemaVersion']='SmallAppPreservationPointBinding/v2'
    elif change=='source':binding['sourceConfigRef']='other-source'
    elif change=='reference':binding['reference']='preservation-'+'a'*64
    elif change=='policy':binding['sourcePolicyPin']=put(h['root']/'same-policy-other-path.json',h['v2_policy'])
    elif change=='point-pin':binding['pointPin']['bytes']=True
    elif change=='control-pin':binding['controlConfigurationPin']['sha256']='Z'*64
    else:binding['publicationOperationId']='../escape'
    with pytest.raises(RepositoryError,match='^PRESERVATION_SOURCE_BOUND_INPUT_INVALID$'):
        describe(h,request,binding)


@pytest.mark.parametrize('change',['schema','extra','action','parent','old-operation','source','reference','target-type'])
def test_new_request_must_be_exact_distinct_restore_for_same_source_point(unchanged,change):
    h=unchanged;request,binding=inputs(h)
    if change=='schema':request['schemaVersion']='SmallAppBackupUiRequest/v2'
    elif change=='extra':request['trusted']=True
    elif change=='action':request['action']='FULL'
    elif change=='parent':request['parentChainRef']='old-parent'
    elif change=='old-operation':request['operationId']=binding['publicationOperationId']
    elif change=='source':request['sourceConfigRef']='other-source'
    elif change=='reference':request['recoveryPointRef']='preservation-'+'a'*64
    else:request['targetConfigRef']=True
    with pytest.raises(RepositoryError,match='^PRESERVATION_SOURCE_BOUND_INPUT_INVALID$'):
        describe(h,request,binding)


@pytest.mark.parametrize('kind',['intent','hold'])
def test_missing_fixed_hold_is_typed_without_reading_other_history(unchanged,kind):
    h=unchanged;request,binding=inputs(h)
    directory=h['repository']/'.repository-control/preservation-holds'
    path=Path(h['hold_intent']['path']) if kind=='intent' else directory/'original_restore.json'
    path.unlink()
    with pytest.raises(RepositoryError,match='^PRESERVATION_SOURCE_BOUND_HOLD_MISSING$'):
        describe(h,request,binding)


@pytest.mark.parametrize('kind',['point-pin','reference'])
def test_binding_must_equal_original_selected_pin_and_derived_reference(unchanged,kind):
    h=unchanged;request,binding=inputs(h)
    if kind=='point-pin':binding['pointPin']=dict(binding['pointPin'],sha256='a'*64)
    else:binding['reference']=request['recoveryPointRef']='preservation-'+'a'*64
    with pytest.raises(RepositoryError,match='^PRESERVATION_SOURCE_BOUND_POINT_CHANGED$'):
        describe(h,request,binding)


@pytest.mark.parametrize('kind',['point','final'])
def test_existing_blocked_reason_is_not_turned_into_metadata_success(unchanged,kind):
    h=unchanged;request,binding=inputs(h)
    path=Path(h['point_pin']['path']) if kind=='point' else Path(h['intent_pin']['path']).parent/'preservation.json'
    path.unlink();code='POINT_MISSING' if kind=='point' else 'FINAL_MISSING'
    with pytest.raises(RepositoryError,match='^PRESERVATION_SOURCE_'+code+'$'):
        describe(h,request,binding)


def test_original_pin_drift_and_unimplemented_publisher_resolver_keep_original_errors(derived):
    h=derived;request,binding=inputs(h)
    h['row']['resolverContract']='PreservationRestoreOwner/v1';write_policy(h,[h['row']])
    binding['sourcePolicyPin']=h['v2_pin']
    with pytest.raises(RepositoryError,match='^PRESERVATION_SOURCE_RESOLVER_UNSUPPORTED$'):
        describe(h,request,binding)


def test_caller_unique_raw_budget_is_not_reset_by_bound_helper(unchanged):
    h=unchanged;request,binding=inputs(h);reads=BorrowedReads();reads.maximum=16*1024*1024
    for index in range(4):reads.read(sized_metadata(h['root']/('shared-'+str(index)+'.json'),16*1024*1024))
    assert reads.total==64*1024*1024
    with pytest.raises(RepositoryError,match='^PRESERVATION_SOURCE_METADATA_LIMIT$'):
        describe(h,request,binding,reads)
    assert reads.total==64*1024*1024
