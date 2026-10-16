"""R3 changed action/grant/host contract only; no browser or rehearsal fixtures."""
import datetime as dt
import json
from pathlib import Path

import pytest

from test_recovery_verification_lab import fixture, admit
from core import VerificationError, json_pin
from lab_boundary import LAB_ACTIONS


def test_action_contract_matches_root_and_frozen_wire():
    root=Path(__file__).resolve().parents[2]
    contract=json.loads((root/'doc/tasks/20261010-backup-restore-modular-development/backup-server-rehearsal-20261012.json').read_bytes())
    selected=contract['nativeLabContinuation20261012']['integrationContinuation20261012R3']['contractClarification']['scopeAllowedActions']
    wire=json.loads((root/'doc/tasks/20261010-backup-restore-modular-development/record-schemas.json').read_bytes())
    assert LAB_ACTIONS==set(selected)
    assert LAB_ACTIONS<=set(wire['$defs']['OperationRequest']['properties']['action']['enum'])
    assert len(LAB_ACTIONS)==12


@pytest.mark.parametrize('actions', [['VERIFY_RECOVERY'], sorted(LAB_ACTIONS), ['PLAN_REHEARSAL','VERIFY_RECOVERY']])
def test_selected_scope_subset_is_valid_without_all_actions(tmp_path,actions):
    assert admit(fixture(tmp_path,('scope','allowedActions',actions))).grant['actions']==['VERIFY_RECOVERY']


@pytest.mark.parametrize('alias',['FULL','INCREMENTAL','READBACK','RESTORE_TO_ISOLATED'])
def test_previous_tokens_are_rejected_without_alias(tmp_path,alias):
    with pytest.raises(VerificationError,match='LAB_ACTION_SCOPE_INVALID'):
        admit(fixture(tmp_path,('scope','allowedActions',[alias,'VERIFY_RECOVERY'])))


def test_current_request_action_must_be_in_scope(tmp_path):
    with pytest.raises(VerificationError,match='LAB_REQUEST_ACTION_NOT_SCOPED'):
        admit(fixture(tmp_path,('scope','allowedActions',['READBACK_VERIFY'])))


@pytest.mark.parametrize('actions',[['READBACK_VERIFY'],['PREPARE_TARGET']])
def test_current_grant_must_authorize_current_action(tmp_path,actions):
    with pytest.raises(VerificationError,match='LAB_GRANT_ACTION_OR_OPERATION_MISMATCH'):
        admit(fixture(tmp_path,('grant','actions',actions)))


@pytest.mark.parametrize('actions',[['FULL'],['CONTROLLED_CUTOVER'],['VERIFY_RECOVERY','VERIFY_RECOVERY'],None])
def test_unknown_duplicate_or_missing_grant_actions_fail(tmp_path,actions):
    with pytest.raises(VerificationError,match='LAB_GRANT_ACTIONS_INVALID'):
        admit(fixture(tmp_path,('grant','actions',actions)))


@pytest.mark.parametrize('change,code',[
    (('grant','approved',False),'LAB_TARGET_GRANT_LEASE_INVALID'),
    (('lease','state','RELEASED'),'LAB_TARGET_GRANT_LEASE_INVALID'),
    (('lease','fenceToken',True),'LAB_TARGET_GRANT_LEASE_INVALID'),
    (('grant','operationId','other'),'LAB_GRANT_ACTION_OR_OPERATION_MISMATCH'),
    (('grant','schemaVersion','UnknownGrant/v1'),'LAB_AUTHORITY_RECORD_UNKNOWN'),
    (('lease','schemaVersion','UnknownLease/v1'),'LAB_AUTHORITY_RECORD_UNKNOWN'),
    (('grant','expiresAt','2020-01-01T00:00:00Z'),'LAB_AUTHORITY_EXPIRED'),
    (('lease','expiresAt','2020-01-01T00:00:00Z'),'LAB_AUTHORITY_EXPIRED'),
    (('host','hostOs','linux'),'LAB_NATIVE_HOST_INVALID'),
    (('host','hostOs','Windows'),'LAB_NATIVE_HOST_INVALID'),
])
def test_selected_grant_lease_and_host_require_actual_contract(tmp_path,change,code):
    with pytest.raises(VerificationError,match=code):
        admit(fixture(tmp_path,change))


def test_copy_protection_requires_exact_readback_verify_token(tmp_path):
    values=fixture(tmp_path,('scope','allowedActions',['VERIFY_RECOVERY']))
    with pytest.raises(VerificationError,match='LAB_READBACK_NOT_RELEASED'):
        admit(values).copy_protection(values[3],300000)


def test_readback_verify_token_consumes_selected_copy_originals(tmp_path):
    values=fixture(tmp_path)
    assert admit(values).copy_protection(values[3],300000)['independentFailureDomain'] is False


def test_signed_repository_grant_and_lease_are_consumed(tmp_path):
    assert admit(fixture(tmp_path,repository_authority=True)).grant['schemaVersion']=='RepositoryAuthorization/v1'


@pytest.mark.parametrize('change,code',[
    (('grant','repositoryId','other'),'LAB_GRANT_REPOSITORY_MISMATCH'),
    (('lease','operationId','other'),'LAB_GRANT_ACTION_OR_OPERATION_MISMATCH'),
    (('grant','actions',['BACKUP_FULL']),'LAB_GRANT_ACTION_OR_OPERATION_MISMATCH'),
    (('grant','expiresAt','2020-01-01T00:00:00Z'),'LAB_AUTHORITY_EXPIRED'),
])
def test_signed_repository_current_authority_mismatch_is_rejected(tmp_path,change,code):
    with pytest.raises(VerificationError,match=code):
        admit(fixture(tmp_path,change,repository_authority=True))
