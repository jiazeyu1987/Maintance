"""Signed local protocol fixtures never represent actual remote recovery."""
import base64
from pathlib import Path
import sys

import pytest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'ops'/'recovery'))
from recovery_engine import RecoveryError, canonical, pin, write
from recovery_cutover_terminal import remote_terminal
from recovery_cli import KEYS


def terminal_fixture(tmp_path, **exit_changes):
    key=Ed25519PrivateKey.generate();path=tmp_path/'key.pem'
    path.write_bytes(key.public_key().public_bytes(Encoding.PEM,PublicFormat.SubjectPublicKeyInfo));public=pin(path)
    intent=write(tmp_path/'intent.json',{'localProtocolOnly':True,'startedAt':'2026-01-01T00:00:00Z'})
    host=write(tmp_path/'host.json',{'localProtocolOnly':True})
    expected=dict(operationId='op',action='STOP_SOURCE_WRITES',targetIdentityPin=host,sourceScopePin=host,
                  recoveryPoint='point',executionHostIdentityPin=host)
    process=write(tmp_path/'process.json',dict(schemaVersion='RecoveryRemoteProcess/v1',nativePid=123,processStartIdentity='boot:123:42',
                 commandIntentPin=intent,startedAt='2026-01-01T00:00:00Z',**expected))
    exit_record=dict(schemaVersion='RecoveryRemoteWait/v1',originalProcessPin=process,waitedPid=123,processStartIdentity='boot:123:42',
                     actualExitCode=0,processTerminated=True,timedOut=False,finishedAt='2026-01-01T00:00:01Z')
    exit_record.update(exit_changes);exit_pin=write(tmp_path/'wait.json',exit_record)
    payload=dict(schemaVersion='RecoveryRemoteTerminal/v1',commandIntentPin=intent,originalProcessPin=process,exitEvidencePin=exit_pin,
                 validFrom='2026-01-01T00:00:02Z',validUntil='2099-01-01T00:00:00Z',**expected)
    signed=dict(schemaVersion='RecoveryRemoteSignedTerminal/v1',keySha256=public['sha256'],payload=payload,
                signature=base64.b64encode(key.sign(canonical(payload))).decode())
    return write(tmp_path/'signed.json',signed),intent,expected,{'remoteTerminalKeyPins':[public]}


def test_remote_native_process_and_wait_are_consumed(tmp_path):
    ref,intent,expected,policy=terminal_fixture(tmp_path)
    refs=remote_terminal(ref,intent,expected,policy)
    assert len(refs) == 3 and refs[0] == ref


@pytest.mark.parametrize('changes',[{'processTerminated':False},{'timedOut':True},{'actualExitCode':True},
                                    {'actualExitCode':1},{'waitedPid':124},{'processStartIdentity':'reused-pid'}])
def test_client_zero_does_not_override_missing_remote_termination(tmp_path,changes):
    ref,intent,expected,policy=terminal_fixture(tmp_path,**changes)
    with pytest.raises(RecoveryError,match='REMOTE_ORIGINAL_PROCESS_TERMINATION_NOT_PROVEN'):
        remote_terminal(ref,intent,expected,policy)


def test_wrong_operation_and_unsigned_tamper_are_rejected(tmp_path):
    from recovery_engine import pinned_json
    ref,intent,expected,policy=terminal_fixture(tmp_path)
    with pytest.raises(RecoveryError,match='REMOTE_TERMINAL_BINDING_INVALID'):
        remote_terminal(ref,intent,dict(expected,operationId='different'),policy)
    value=pinned_json(ref);value['payload']['action']='RELEASE_TARGET_WRITES';ref=write(ref['path'],value)
    with pytest.raises(InvalidSignature):remote_terminal(ref,intent,expected,policy)


def test_controlled_public_keys_match_frozen_entry():
    assert KEYS['CONTROLLED_CUTOVER'] == {'repositoryPoint','recoveryVerificationReport'}


def test_controlled_readonly_mode_admission_precedes_fence_requirement(tmp_path,monkeypatch):
    from recovery_plan import controlled_protection, controlled_preconditions
    from recovery_cutover_fence import CONTEXT_KEY
    monkeypatch.delenv(CONTEXT_KEY,raising=False)
    config={'controlledPreconditions':dict(restoreKind='REBUILD_EMPTY',protectionPointPin=None,verificationReportPin=None,
                                         sourceFencePin=None,validUntil='2099-01-01T00:00:00Z')}
    controlled_protection({},config,{'restoreMode':'REBUILD_EMPTY'},{})
    with pytest.raises(RecoveryError,match='CONTROLLED_FENCE_HANDOFF_REQUIRED'):
        controlled_preconditions({},config,{'restoreMode':'REBUILD_EMPTY'},{})
