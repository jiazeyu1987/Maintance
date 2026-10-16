"""R2 local protocol/fault checks; never native backup/restore acceptance.

Use W03's actual configuration, signing, catalog and original-retention code
with its local publication fixture. No signed_evidence mock or native service.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

import pytest
from cryptography.exceptions import InvalidSignature

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'ops/recovery'))
import recovery_cli as cli
import recovery_engine as engine
import recovery_engine_read_guard as read_guard_module
from recovery_engine import Budget, RecoveryError, canonical, load, pin, pinned_json, write
from recovery_engine_read_guard import RepositoryReadGuard
from recovery_plan import legacy_completion, signed_evidence
from test_recovery_static_repair_r4 import local_executor, repository_fixture


@pytest.mark.parametrize('native_directory_fault', [False, True], ids=['portable-protocol', 'linux-native-fsync'])
def test_guard_unlink_sync_restore_double_failure_cannot_publish_success_cache(
        tmp_path, monkeypatch, native_directory_fault):
    if native_directory_fault and sys.platform != 'linux':
        pytest.skip('Linux directory fsync fault required; no WSL/native recovery execution authorized')
    request, _, policy = repository_fixture(tmp_path)
    evidence = tmp_path/'evidence'; evidence.mkdir(mode=0o700)
    identity = write(tmp_path/'identity.json', {'protocolOnly':'target'})
    policy.update(evidenceRoot=str(evidence), dataTargetPin=write(tmp_path/'target.json', {'targetIdentityPin':identity}),
                  recordSchemasPin=write(tmp_path/'schema.json', {}))
    input_ref = write(tmp_path/'input.json', {'protocolOnly':True})
    request.update(action='RESTORE_EXECUTE', deadlineMilliseconds=5000,
                   inputPins={'restorePlan':input_ref, 'recoveryTarget':input_ref})
    request_pin = write(tmp_path/'request.json', request)
    output = tmp_path/'public-result.json'
    # Isolated state protocol: no real target, authority or restore is claimed.
    monkeypatch.setattr(cli, 'trusted_configuration', lambda request:({},policy,{}))
    monkeypatch.setattr(cli, 'authorities', lambda *args:None)
    monkeypatch.setattr(cli, 'validate_record', lambda value,*args:value)
    if not native_directory_fault:
        monkeypatch.setattr(RepositoryReadGuard, 'child_options', lambda self,env,fds=():dict(env=env))
    python, script = local_executor(tmp_path, 'SUCCEEDED')
    calls = []
    def harmless_protocol_operation(operation):
        calls.append('dispatched')
        operation.runner.run(python, script, dict(operationId='op',requestId='req',action='PROTOCOL'), guard=lambda:None)
        return {'protocolOnly':True}
    monkeypatch.setattr(cli.RecoveryOperation, 'run', harmless_protocol_operation)
    control = tmp_path/'repo'/'.repository-control'
    marker = control/'recovery-read-guard.json'
    events = []
    def directory_fault(path):
        assert Path(path) == control and not marker.exists()  # Actual unlink has happened.
        journal = next(evidence.glob('request-*.json'))
        assert load(journal)['state'] == 'RUNNING'  # Success cache has not been published.
        events.append('directory-durability-failed-after-unlink')
        raise OSError('ENGINEERING_INJECTED_CONTROL_DIRECTORY_DURABILITY_FAILURE')
    if native_directory_fault:
        actual_fsync = os.fsync
        def native_fsync(fd):
            actual = os.fstat(fd); expected = control.stat()
            if (actual.st_dev,actual.st_ino) == (expected.st_dev,expected.st_ino):
                return directory_fault(control)
            return actual_fsync(fd)
        monkeypatch.setattr(os, 'fsync', native_fsync)
    else:
        # Exercises identical exception order on Windows, not Linux fsync proof.
        monkeypatch.setattr(read_guard_module, '_sync_control_directory', directory_fault)
    actual_guard_write = read_guard_module.write
    def restore_before_replace_fault(path, value):
        if Path(path) == marker and value['state'] == 'TERMINAL_UNKNOWN':
            assert not marker.exists()
            events.append('unknown-marker-restore-failed-before-replace')
            raise OSError('ENGINEERING_INJECTED_MARKER_RESTORE_BEFORE_REPLACE_FAILURE')
        return actual_guard_write(path, value)
    monkeypatch.setattr(read_guard_module, 'write', restore_before_replace_fault)
    assert cli.main(['--request',request_pin['path'],'--output',str(output)]) == 2
    assert events == ['directory-durability-failed-after-unlink','unknown-marker-restore-failed-before-replace']
    assert not marker.exists() and len(calls) == 1
    result_path = next(evidence.glob('operation-*/operation-result.json'))
    journal_path = next(evidence.glob('request-*.json'))
    target_path = next(evidence.glob('target-*.state.json'))
    result = load(result_path); journal = load(journal_path)
    assert result['state'] == journal['state'] == load(target_path)['state'] == load(output)['state'] == 'TERMINAL_UNKNOWN'
    assert pinned_json(journal['resultPin']) == result and result['actualExitCode'] == 0
    receipt = next((result_path.parent).glob('invocation-*/exit.json'))
    assert load(receipt)['actualExitCode'] == 0
    before = result_path.read_bytes(), journal_path.read_bytes(), target_path.read_bytes()
    assert cli.main(['--request',request_pin['path'],'--output',str(output)]) == 2
    assert load(output)['state'] == 'TERMINAL_UNKNOWN' and len(calls) == 1
    assert before == (result_path.read_bytes(),journal_path.read_bytes(),target_path.read_bytes())
    request['requestId'] = 'different-request-same-target'
    changed = write(tmp_path/'different-request.json', request)
    assert cli.main(['--request',changed['path'],'--output',str(output)]) == 2
    assert load(output)['failureCode'] == 'TARGET_PREVIOUS_EXECUTION_RECONCILIATION_REQUIRED'
    assert load(output)['state'] == 'TERMINAL_UNKNOWN' and len(calls) == 1


PEER = Path('C:/Users/BJB110/.codex/worktrees/instance-snapshot-integration/IntRuoyiMaintance')


@pytest.fixture
def w03_publication(tmp_path):
    # Missing selected producer files are a test prerequisite failure; no copy
    # or invented producer replaces the actual approved W03 workspace.
    fixture_path = PEER/'scripts/tests/test_repository_chain.py'
    assert fixture_path.is_file()
    sys.path.insert(0, str(PEER/'ops/recovery'))
    try:
        spec = importlib.util.spec_from_file_location('w04_actual_w03_local_fixture', fixture_path)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(PEER/'ops/recovery'))
    from repository_records import retain_original, sign_record, write_new
    class SeparateEvidencePublication(module.LocalRepository):
        def record(self, name, value):
            if name.endswith('-process.json'):
                label = name.removesuffix('-process.json')
                request = self.request('BACKUP_FULL', suffix=label)
                request.update(operationId='local-'+label, requestId='offline-capture-'+label)
                self.authorize(request, self.source)
                folder = self.evidence/hashlib.sha256(request['requestId'].encode()).hexdigest()
                folder.mkdir()
                request_pin = write_new(folder/'request.json', request)
                # Installer original shape, local fixture identity only. This
                # is not an actual native capture terminal or NAS proof.
                return write_new(folder/'installer-1-original-owner.json', dict(
                    schemaVersion='RepositoryOriginalProcess/v1', requestPin=request_pin,
                    binding={'operationId':request['operationId'],'attemptId':label},
                    ownerPid=os.getpid(), processStartTicks=1, ownerCommand='OFFLINE_PROTOCOL_ONLY'))
            return super().record(name, value)
    producer = SeparateEvidencePublication(tmp_path)
    ref = producer.point('full')
    point = pinned_json(ref)
    original = signed_evidence(point['originalExitEvidencePin'], {'repositoryEvidenceKeyPins':[producer.verifying]})['originalProcessPin']
    assert producer.config.evidence in Path(original['path']).parents
    assert producer.config.root not in Path(original['path']).parents
    archive_copy = Path(ref['path']).parent/'original-process.json'
    retain_original(archive_copy, original)  # Actual W03 archive copy; signed Pin stays external.
    producer.catalog.load(ref)  # Actual W03 signed completion, material, archive and original validation.
    policy = dict(repositoryId='local', repositoryPointPins=[ref], repositoryEvidenceKeyPins=[producer.verifying],
        readbackRule={'requiredValues':{'independentConnection':True,'serverDurabilityVerified':False}},
        originalExitRule={'requiredValues':{'actualExitCode':0,'processTerminated':True,'rawTerminalVerified':True}})
    request = dict(operationId='offline-w04-consume',requestId='offline-w04-consume',selectedPointPin=ref)
    request_pin = write(tmp_path/'w04-request.json', request)
    return producer, ref, point, original, archive_copy, policy, request, request_pin


def consume_completion(ref, point, policy, request, request_pin):
    with RepositoryReadGuard(request, request_pin, policy, Budget(10000)) as guard:
        guard.point(ref)
        guard.archive_pins(ref, [point[name] for name in
            ('manifestPin','ownerCloseEvidencePin','readbackEvidencePin','originalExitEvidencePin')] + point['payloadRefs'])
        manifest = legacy_completion(point, policy)
        guard.finish(terminal_known=True)
        return manifest


def test_actual_w03_separate_evidence_original_consumed_without_pin_relocation(w03_publication):
    producer, ref, point, original, archive_copy, policy, request, request_pin = w03_publication
    before = [Path(point[k]['path']).read_bytes() for k in ('ownerCloseEvidencePin','readbackEvidencePin','originalExitEvidencePin')]
    manifest = consume_completion(ref, point, policy, request, request_pin)
    assert manifest == pinned_json(point['manifestPin'])
    for field in ('ownerCloseEvidencePin','readbackEvidencePin','originalExitEvidencePin'):
        assert signed_evidence(point[field], policy)['originalProcessPin'] == original
    assert archive_copy.read_bytes() == Path(original['path']).read_bytes() and pin(archive_copy) != original
    assert before == [Path(point[k]['path']).read_bytes() for k in ('ownerCloseEvidencePin','readbackEvidencePin','originalExitEvidencePin')]
    producer.config.current(); producer.catalog.load(ref)


@pytest.mark.parametrize('fault', ['different-original','different-operation','different-manifest','pin-drift',
    'missing-external-with-archive-copy','unknown-key','key-drift','invalid-signature','current-rule','crossrepo-archive'])
def test_w03_completion_and_original_trust_gates_remain_enforced(w03_publication, fault):
    producer, ref, point, original, archive_copy, policy, request, request_pin = w03_publication
    from repository_records import sign_record, write_new
    expected = RecoveryError; code = None
    if fault in ('different-original','different-operation','different-manifest','invalid-signature'):
        record = signed_evidence(point['originalExitEvidencePin'], policy)
        if fault == 'different-original':
            record['originalProcessPin'] = write(producer.evidence/'wrong-process.json', {'offlineWrongOriginal':True})
            code = 'OWNER_CLOSE_OR_ORIGINAL_EXIT_NOT_COMPLETE'
        elif fault == 'different-operation':
            record['operationId'] = 'different-operation'; code = 'OWNER_CLOSE_OR_ORIGINAL_EXIT_NOT_COMPLETE'
        elif fault == 'different-manifest':
            record['manifestPin'] = write(producer.evidence/'wrong-manifest.json', {'offlineWrongManifest':True})
            code = 'REPOSITORY_EVIDENCE_BINDING_INVALID'
        envelope = sign_record(record, producer.signing, [producer.verifying])
        if fault == 'invalid-signature':
            envelope['payload']['operationId'] = 'unsigned-change'; expected = InvalidSignature
        point['originalExitEvidencePin'] = write_new(Path(ref['path']).parent/'fault-original-exit.json', envelope)
    elif fault == 'pin-drift':
        Path(original['path']).write_bytes(b'changed exact external original'); code = 'PIN_CHANGED'
    elif fault == 'missing-external-with-archive-copy':
        assert archive_copy.exists(); Path(original['path']).unlink(); expected = FileNotFoundError
    elif fault == 'unknown-key':
        policy['repositoryEvidenceKeyPins'] = [producer.public]; code = 'REPOSITORY_EVIDENCE_AUTHORITY_UNKNOWN'
    elif fault == 'key-drift':
        Path(producer.verifying['path']).write_bytes(b'changed provisioned public key'); code = 'PIN_CHANGED'
    elif fault == 'current-rule':
        policy['originalExitRule']['requiredValues']['actualExitCode'] = 1; code = 'ORIGINAL_EVIDENCE_NOT_COMPLETE'
    else:
        sibling = producer.base/'other-repository'/'archives'/'full'/'.repository'; sibling.mkdir(parents=True)
        foreign = write(sibling/'manifest.json', pinned_json(point['manifestPin']))
        point['manifestPin'] = foreign; code = 'READ_GUARD_ARCHIVE_BINDING_INVALID'
    with pytest.raises(expected, match=code):
        consume_completion(ref, point, policy, request, request_pin)
    marker = producer.repo/'.repository-control'/'recovery-read-guard.json'
    assert load(marker)['state'] == 'TERMINAL_UNKNOWN'
