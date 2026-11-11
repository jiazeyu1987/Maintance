"""Actual Linux publication/handoff/strict history; finite service protocols.

Requires the existing authentic SAFE semantic carrier used by the preservation
tests. No server/Docker is contacted; no validator success is substituted.
This is source-evidence verification, actualBusinessRestore remains False.
"""
from copy import deepcopy
import sys
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'ops/recovery'),str(ROOT/'ops/backup_engine/formal')]
from test_recovery_target_preservation_handoff import (handoff_case,publication_case,
    capture_protocol,original_capture_protocol,case,restore_case,claim,locked,started,context,construct,quiesce)
from recovery_engine import Budget,RecoveryError,pin,pinned_json,write
from repository_records import RepositoryError
import recovery_target_preservation as publisher
from recovery_preservation_source import list_preservation_points,resolve_preservation_source


def test_v2_unchanged_publisher_real_history_keeps_strict_validator_and_original_facts(handoff_case):
    assert sys.platform.startswith('linux'),'TEST_REQUIRES_REAL_LINUX_NOT_A_SKIP'
    h=handoff_case;claim(h.case)
    with locked(h.case) as fd:
        _,binding,_=started(h,fd)
        with context(h,binding,fd,budget=Budget(240000)) as ctx:
            native=construct(h,ctx)
            publication=publisher.TargetPreservation.prepare(native,policy_pin=h.preservation_policy,
                reservation_pin=h.reservation)
            quiesce(h,native)
            publication.capture_and_publish()
            final=publication.handoff().reference
        assert publication._closed and publication._repository_lock.stream.closed
    original_binding=pinned_json(binding)
    policy=dict(schemaVersion='MainTargetPreservationSourcePolicy/v2',sourceConfigRef='preserved-main58',
        originTargetConfigRef=h.request['targetConfigRef'],repositoryConfigurationPin=h.repository_pin,
        publisherBindings=[dict(kind='UNCHANGED_OWNER',configurationPin=write(h.case['root']/'trusted-publisher-owner.json',h.owner),
            preservationPolicyPin=h.preservation_policy)],maxPoints=8,maxDocumentBytes=4*1024*1024,
        maxMetadataBytes=64*1024*1024)
    policy_pin=write(h.case['root']/'preservation-source-policy.json',policy)
    listing=list_preservation_points(policy_pin,guard=lambda:None)
    row,=listing['points'];assert row['status']=='PRESERVATION_PUBLISHED'
    assert listing['payloadContentVerified'] is row['restoreVerified'] is False
    new_request=deepcopy(h.request)
    new_request.update(operationId='new_source_restore',sourceConfigRef=policy['sourceConfigRef'],
        recoveryPointRef=row['reference'],parentChainRef=None,targetConfigRef='target59')
    new_pin=write(h.case['root']/'new-source-request.json',new_request)
    originals={str(p):p.read_bytes() for p in h.case['root'].rglob('*') if p.is_file()}
    actions=deepcopy(h.engine.actions)
    result=resolve_preservation_source(policy_pin,new_pin,guard=lambda:None)
    assert result['schemaVersion']=='MainTargetPreservationRestoreAdmission/v1'
    assert result['requestPin']==new_pin and result['sourcePolicyPin']==policy_pin
    assert result['pointPin']==row['pointPin'] and result['targetPreservationPin']==final
    assert result['historicalRequestPin']==original_binding['requestPin']
    assert result['historicalConfigurationPin']==original_binding['configurationPin']
    assert result['executionBindingPin']==binding
    assert result['payloadContentVerified'] is True
    assert result['clearAuthorized'] is result['targetAdmitted'] is False
    assert result['controlledRestoreEligible'] is result['sourceRestored'] is False
    assert result['incrementalParentEligible'] is result['programArchiveVerified'] is False
    validation=result['preservationValidation']
    assert validation['schemaVersion']=='MainTargetPreservationEvidenceValidation/v1'
    assert validation['targetPreservationPin']==final and validation['clearAuthorized'] is False
    assert validation['captureInvocations'] and validation['originalResultPins']
    assert h.engine.actions==actions
    assert all(Path(path).read_bytes()==raw for path,raw in originals.items())
    # The genuine validator must consume actual archived bytes, not just pins
    # or the shallow catalogue's metadata claims.
    point=pinned_json(row['pointPin'])
    payload=Path(point['payloadRefs'][0]['path']);payload.write_bytes(b'changed actual archived bytes')
    with pytest.raises((RecoveryError,RepositoryError)) as caught:
        resolve_preservation_source(policy_pin,new_pin,guard=lambda:None)
    assert 'PRESERVATION_' in str(caught.value)
    assert h.engine.actions==actions
