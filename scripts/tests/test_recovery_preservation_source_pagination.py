"""Actual bounded metadata files, never source admission or a business restore."""
from copy import deepcopy
import hashlib
import json
import os
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
from test_recovery_preservation_source_publishers import derived,load,write_policy
from test_recovery_restore_inputs import sized_metadata

MIB=1024*1024
PAGE_FIELDS=set(('schemaVersion sourceConfigRef sourcePolicyPin repositoryConfigurationPin role snapshotDigest '
    'discoveredCount pageCount metadataBytes points nextCursor complete payloadContentVerified clearAuthorized '
    'originalResultPins').split())
SELECTION_FIELDS=set(('schemaVersion sourceConfigRef sourcePolicyPin repositoryConfigurationPin role snapshotDigest '
    'reference pointPin point metadataBytes originalResultPins payloadContentVerified sourceAdmissionGranted '
    'targetAdmitted clearAuthorized').split())


@pytest.fixture
def tmp_path(tmp_path_factory):
    return tmp_path_factory.mktemp('p').resolve()


def padded(path,value,size=None):
    raw=canonical(value)
    if size is not None:
        assert len(raw)<size
        raw+=b' '*(size-len(raw))
    path.write_bytes(raw)
    return reference(path)


def operation(h,name,*,large=None,published=True):
    """Coherent finite file protocols, not actual producer success evidence."""
    h['build'](name,published=published)
    intent=load(h['intent_pin']);binding=load(h['binding_pin'])
    binding['policySha256']=digest(h['owner']['targetProgramPolicies']['target58'])
    intent['executionBindingPin']=put(Path(h['binding_pin']['path']),binding)
    intent_pin=put(Path(h['intent_pin']['path']),intent)
    hold_intent=load(h['hold_intent']);hold_intent['preservationIntentPin']=intent_pin
    intent_hold=put(Path(h['hold_intent']['path']),hold_intent)
    point=load(h['point_pin']);manifest_path=Path(point['manifestPin']['path'])
    point['manifestPin']=padded(manifest_path,load(point['manifestPin']),large)
    point_pin=padded(Path(h['point_pin']['path']),point,large)
    proof=load(h['proof_pin']);proof.update(intentPin=intent_pin,holdIntentPin=intent_hold,
        pointPin=point_pin,manifestPin=point['manifestPin'])
    proof_pin=put(Path(h['proof_pin']['path']),proof)
    hold_pin=None
    if published:
        holds=h['repository']/'.repository-control/preservation-holds'
        hold=load(reference(holds/(name+'.json')))
        hold.update(intentPin=intent_hold,pointPin=point_pin,archiveProofPin=proof_pin)
        hold_pin=put(holds/(name+'.json'),hold)
        publication=Path(intent_pin['path']).parent
        handoff=load(reference(publication.parent/'session/handoff.json'));handoff['archiveProofPin']=proof_pin
        handoff_pin=put(publication.parent/'session/handoff.json',handoff)
        final=load(reference(publication/'preservation.json'))
        final.update(intentPin=intent_pin,archiveProofPin=proof_pin,handoffPin=handoff_pin,holdPin=hold_pin)
        put(publication/'preservation.json',final)
    row=dict(operationId=name,holdIntentPin=intent_hold,holdPin=hold_pin,
        pointPin=point_pin if published else None,reference=point_reference(point_pin) if published else None)
    h.setdefault('entries',{})[name]=dict(index=row,pointPin=point_pin,manifestPin=point['manifestPin'],
        intentPin=intent_pin,payload=h['payload'])
    return h['entries'][name]


def source(h):
    h['owner']['targetProgramPolicies']={'target58':{'protocolOnly':'not live'}}
    h['owner_pin']=put(Path(h['owner_pin']['path']),h['owner'])
    row=dict(kind='UNCHANGED_OWNER',configurationPin=h['owner_pin'],preservationPolicyPin=h['preservation_policy'])
    write_policy(h,[row]);h['entries']={}
    return h


@pytest.fixture
def small(metadata):
    h=source(metadata)
    for name in ('restore_a','restore_b','restore_c'):operation(h,name)
    return h


def page(h,**kwargs):
    return consumer.list_preservation_page(h['v2_pin'],guard=kwargs.pop('guard',lambda:None),**kwargs)


def select(h,ref,snapshot,**kwargs):
    return consumer.select_preservation_point(h['v2_pin'],ref,snapshot_digest=snapshot,
        guard=kwargs.pop('guard',lambda:None),**kwargs)


def point_reference(pin):
    return 'preservation-'+hashlib.sha256(canonical(pin)).hexdigest()


def identity(path,exists):
    info=path.stat()
    return dict(path=str(path),exists=exists,device=info.st_dev,inode=info.st_ino,mode=info.st_mode,
        size=info.st_size,modifiedNanoseconds=info.st_mtime_ns,
        changedNanoseconds=info.st_birthtime_ns if os.name=='nt' else info.st_ctime_ns)


def assert_budget(result):
    pins=result['originalResultPins']
    assert len(pins)==len({str(Path(p['path'])) for p in pins})
    assert result['metadataBytes']==sum(pin['bytes'] for pin in pins)<=64*MIB
    assert result['payloadContentVerified'] is result['clearAuthorized'] is False


def test_default_page_exact_snapshot_and_selection_four_flags(small):
    h=small;before={p:p.read_bytes() for p in h['root'].rglob('*') if p.is_file()}
    result=page(h)
    assert set(result)==PAGE_FIELDS and result['schemaVersion']=='MainTargetPreservationPage/v1'
    assert result['discoveredCount']==3 and result['pageCount']==1 and not result['complete']
    assert result['points'][0]['operationId']=='restore_a'
    directory=h['repository']/'.repository-control/preservation-holds'
    entries=[deepcopy(h['entries'][key]['index']) for key in sorted(h['entries'])]
    # Newly observed hold-file pins use the existing file reader's POSIX path
    # representation. Published point pins stay byte-for-byte as archived.
    for entry in entries:
        for key in ('holdIntentPin','holdPin'):
            if entry[key] is not None:entry[key]['path']=Path(entry[key]['path']).as_posix()
    expected=dict(sourcePolicyPin=h['v2_pin'],repositoryConfigurationPin=h['repository_pin'],
        holdDirectoryIdentity=identity(directory,True),entries=entries)
    assert result['snapshotDigest']==hashlib.sha256(canonical(expected)).hexdigest()
    assert_budget(result)
    selected=select(h,h['entries']['restore_c']['index']['reference'],result['snapshotDigest'])
    assert set(selected)==SELECTION_FIELDS and selected['schemaVersion']=='MainTargetPreservationSelection/v1'
    assert selected['point']['operationId']=='restore_c' and selected['pointPin']==h['entries']['restore_c']['pointPin']
    for key in ('payloadContentVerified','sourceAdmissionGranted','targetAdmitted','clearAuthorized'):
        assert selected[key] is False
    assert_budget(selected)
    old=consumer.list_preservation_points(h['v2_pin'],guard=lambda:None)
    assert selected['point']==old['points'][2]
    assert all(p.read_bytes()==raw for p,raw in before.items())


@pytest.mark.parametrize('pending',[False,True],ids=['empty','pending'])
def test_empty_or_pending_directory_never_implies_restore_admission(metadata,pending):
    h=source(metadata)
    if pending:operation(h,'restore_a',published=False)
    result=page(h)
    assert result['complete'] and result['nextCursor'] is None and result['discoveredCount']==int(pending)
    assert result['pageCount']==int(pending)
    if pending:
        assert result['points'][0]['reference'] is result['points'][0]['pointPin'] is None
        assert not result['points'][0]['sourceAdmissionAvailable']
    assert_budget(result)
    with pytest.raises(RepositoryError,match='^PRESERVATION_SOURCE_POINT_UNKNOWN$'):
        select(h,'preservation-'+'a'*64,result['snapshotDigest'])


def test_real_over_64mib_capacity_reads_only_selected_large_metadata_and_stops_at_budget(metadata,monkeypatch):
    h=source(metadata)
    for name in ('restore_a','restore_b','restore_c'):operation(h,name,large=12*MIB)
    large={Path(row[key]['path']) for row in h['entries'].values() for key in ('pointPin','manifestPin')}
    assert sum(path.stat().st_size for path in large)==72*MIB
    payloads={row['payload'] for row in h['entries'].values()};actual=consumer._read_file;opened=[]
    def observed(path,*args,**kwargs):
        path=Path(path);assert path not in payloads,'PAGED_METADATA_OPENED_PAYLOAD'
        opened.append(path);return actual(path,*args,**kwargs)
    monkeypatch.setattr(consumer,'_read_file',observed)
    result=page(h);assert_budget(result)
    assert set(opened)&large=={Path(h['entries']['restore_a'][key]['path']) for key in ('pointPin','manifestPin')}
    snapshot=result['snapshotDigest'];seen=[result['points'][0]['operationId']]
    while result['nextCursor'] is not None:
        opened.clear();result=page(h,cursor=result['nextCursor']);assert_budget(result)
        assert result['snapshotDigest']==snapshot
        name=result['points'][0]['operationId'];seen.append(name)
        assert set(opened)&large=={Path(h['entries'][name][key]['path']) for key in ('pointPin','manifestPin')}
    assert seen==['restore_a','restore_b','restore_c']
    opened.clear();chosen=select(h,h['entries']['restore_c']['index']['reference'],snapshot);assert_budget(chosen)
    assert set(opened)&large=={Path(h['entries']['restore_c'][key]['path']) for key in ('pointPin','manifestPin')}
    result=page(h,limit=32)
    assert result['pageCount']==2 and not result['complete'] and result['nextCursor']['afterOperationId']=='restore_b'
    assert_budget(result)
    with pytest.raises(RepositoryError,match='METADATA_LIMIT'):
        consumer.list_preservation_points(h['v2_pin'],guard=lambda:None)


@pytest.mark.parametrize('limit',[True,False,0,33,1.5])
def test_limit_is_strict_integer_one_to_32(small,limit):
    with pytest.raises(RepositoryError,match='^PRESERVATION_SOURCE_CURSOR_INVALID$'):page(small,limit=limit)


@pytest.mark.parametrize('change',['not-object','schema','extra','oversize','digest','after-type','pin-type'])
def test_cursor_exact_schema_encoding_and_types(small,change):
    cursor=deepcopy(page(small)['nextCursor'])
    if change=='not-object':cursor='not-a-dict'
    elif change=='schema':cursor['schemaVersion']='MainTargetPreservationCursor/v2'
    elif change=='extra':cursor['offset']=1
    elif change=='oversize':cursor['afterOperationId']='a'*4096
    elif change=='digest':cursor['snapshotDigest']='A'*64
    elif change=='after-type':cursor['afterOperationId']=True
    else:cursor['sourcePolicyPin']['bytes']=True
    with pytest.raises(RepositoryError,match='^PRESERVATION_SOURCE_CURSOR_INVALID$'):page(small,cursor=cursor)


def test_generated_cursor_also_obeys_4096_bytes_with_real_long_policy_path(small):
    h=small
    root=Path('\\\\?\\'+str(h['root'])) if os.name=='nt' else h['root']
    while len(str(root))<3800:root=root/('directory-'+'x'*170)
    root.mkdir(parents=True)
    source_pin=put(root/'source-policy.json',h['v2_policy'])
    candidate=dict(schemaVersion='MainTargetPreservationCursor/v1',sourcePolicyPin=source_pin,
        repositoryConfigurationPin=h['repository_pin'],snapshotDigest='a'*64,afterOperationId='restore_a')
    assert len(canonical(candidate))>4096
    with pytest.raises(RepositoryError,match='^PRESERVATION_SOURCE_CURSOR_INVALID$'):
        consumer.list_preservation_page(source_pin,guard=lambda:None)


@pytest.mark.parametrize('change',['add','delete','same-bytes-replace','directory-time','policy-pin','digest','after'])
def test_cursor_or_selection_restarts_when_index_or_bound_identity_changes(small,change):
    h=small;first=page(h);cursor=deepcopy(first['nextCursor'])
    directory=h['repository']/'.repository-control/preservation-holds'
    if change=='add':operation(h,'restore_d')
    elif change=='delete':Path(h['entries']['restore_c']['index']['holdPin']['path']).unlink()
    elif change=='same-bytes-replace':
        path=Path(h['entries']['restore_c']['index']['holdPin']['path']);raw=path.read_bytes()
        path.rename(h['root']/'kept-hold.json');path.write_bytes(raw)
    elif change=='directory-time':
        info=directory.stat();os.utime(directory,ns=(info.st_atime_ns,info.st_mtime_ns+1000000000))
    elif change=='policy-pin':cursor['sourcePolicyPin']=put(h['root']/'same-policy.json',h['v2_policy'])
    elif change=='digest':cursor['snapshotDigest']='a'*64
    else:cursor['afterOperationId']='missing_operation'
    with pytest.raises(RepositoryError,match='^PRESERVATION_CATALOGUE_CHANGED_RESTART$'):page(h,cursor=cursor)
    if change in ('add','delete','same-bytes-replace','directory-time'):
        with pytest.raises(RepositoryError,match='^PRESERVATION_CATALOGUE_CHANGED_RESTART$'):
            select(h,h['entries']['restore_a']['index']['reference'],first['snapshotDigest'])


def test_unread_point_drift_is_not_promised_by_snapshot_and_never_becomes_normal_end(small):
    h=small;first=page(h)
    Path(h['entries']['restore_b']['pointPin']['path']).write_bytes(b'{}')
    again=page(h);assert again['snapshotDigest']==first['snapshotDigest']
    for action in (lambda:page(h,cursor=first['nextCursor']),lambda:page(h,limit=32),
            lambda:select(h,h['entries']['restore_b']['index']['reference'],first['snapshotDigest'])):
        with pytest.raises(RepositoryError,match='PIN_CHANGED'):action()


@pytest.mark.parametrize('change',['oversize','entry-count','intent-count','duplicate-point','foreign-origin','wrong-point-path'])
def test_small_index_limits_and_typed_scope_precede_any_large_point(small,monkeypatch,change):
    h=small;directory=h['repository']/'.repository-control/preservation-holds'
    if change=='oversize':
        path=Path(h['entries']['restore_a']['index']['holdPin']['path']);padded(path,load(reference(path)),65537)
        expected='INDEX_LIMIT'
    elif change in ('entry-count','intent-count'):
        h['v2_policy']['maxPoints']=1 if change=='entry-count' else 2
        if change=='intent-count':
            for entry in h['entries'].values():Path(entry['index']['holdPin']['path']).unlink()
        h['v2_pin']=put(Path(h['v2_pin']['path']),h['v2_policy'])
        expected='POINT_LIMIT|HOLD_SET_INVALID'
    else:
        path=Path(h['entries']['restore_c']['index']['holdPin']['path']);value=load(reference(path))
        if change=='duplicate-point':value['pointPin']=h['entries']['restore_a']['pointPin']
        elif change=='foreign-origin':value['targetConfigRef']='target59'
        else:value['pointPin']=h['identity_pin']
        put(path,value);expected='POINT_DUPLICATE|HOLD_SCOPE_CHANGED|HOLD_BINDING_CHANGED|HISTORICAL_PATH_CHANGED'
    actual=consumer._read_file
    forbidden={Path(entry[key]['path']) for entry in h['entries'].values() for key in ('pointPin','manifestPin')}
    def observed(path,*args,**kwargs):
        assert Path(path) not in forbidden,'INVALID_SMALL_INDEX_OPENED_LARGE_POINT'
        return actual(path,*args,**kwargs)
    monkeypatch.setattr(consumer,'_read_file',observed)
    with pytest.raises(RepositoryError,match=expected):page(h)


def test_page_and_choice_keep_actual_a1_originals_and_unique_shared_meter(derived):
    h=derived;result=page(h);assert_budget(result)
    selected=select(h,result['points'][0]['reference'],result['snapshotDigest']);assert_budget(selected)
    for original in [h['a1'].base_pin,*h['a1'].originals.values(),*h['a1'].binding['evidencePins']]:
        assert any(Path(pin['path'])==Path(original['path']) and pin['sha256']==original['sha256']
            for pin in selected['originalResultPins'])
    assert selected['sourceAdmissionGranted'] is selected['targetAdmitted'] is False


def test_single_row_over_budget_is_explicit_and_not_empty_success(metadata):
    h=source(metadata);operation(h,'restore_a',large=12*MIB)
    h['v2_policy']['maxMetadataBytes']=16*MIB;h['v2_pin']=put(Path(h['v2_pin']['path']),h['v2_policy'])
    with pytest.raises(RepositoryError,match='^RESTORE_INPUTS_METADATA_LIMIT$'):page(h)


def test_index_uses_same_remaining_raw_budget_before_any_history(small):
    h=small
    # All bytes are real files. The page's already consumed metadata cannot
    # be reset when the small index begins; no native success is substituted.
    reads=consumer._Reads(lambda:None)
    policy,repository=consumer._policy(reads,h['v2_pin'])
    remaining=64*MIB-reads.total
    sizes=[16*MIB]*3+[remaining-48*MIB]
    for index,size in enumerate(sizes):reads.read(sized_metadata(h['root']/('fill-'+str(index)+'.json'),size))
    with pytest.raises(RepositoryError,match='METADATA_LIMIT'):
        consumer._hold_index(reads,policy,repository)
