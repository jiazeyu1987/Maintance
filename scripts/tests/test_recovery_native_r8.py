"""R8 local record/refusal checks. Fixtures are not Linux runtime attestations."""
import ast
import base64
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import stat
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'ops/recovery'))
from recovery_environment_contract import EnvironmentFailure
from recovery_native_process import authenticate_payload, signer_socket_metadata, IndependentAuthoritySigner
from recovery_native_launcher import selected_signing_runtime, selected_graph_pins, admit_installation_entry
from recovery_native_observation import RESULT_FIELDS, wire_canonical
from recovery_native_service_identity import SERVICE_FIELDS
from recovery_native_installation_admission import (ADMISSION_FIELDS, ADMISSION_SCHEMA,
    installation_argv, installation_sources, validate_admission_records)

LAB = '/mnt/intruoyi-data/backup-restore-lab/20261012-w01-w07'
REHEARSAL = 'backup-server-rehearsal-20261012-r1'


def reference(name):
    raw = name.encode()
    return dict(path=LAB + '/' + name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def signed_identity(payload):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    key = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    sha = hashlib.sha256(public).hexdigest()
    envelope = dict(schemaVersion='RepositorySignedRecord/v1', keySha256=sha, payload=payload,
                    signature=base64.b64encode(key.sign(wire_canonical(payload))).decode())
    return authenticate_payload(envelope, public, sha)


@pytest.mark.parametrize('damage', [None, 'foreign-runtime', 'wrong-binding', 'extra-runtime-field', 'absent-identity'])
def test_exact_observe_derives_runtime_from_authenticated_identity(damage):
    proof = reference('proof'); binding_pin = reference('binding')
    launch = dict(operationRequestPin=reference('request'))
    installation = dict(nativeRuntimeProofPin=proof)
    provision = dict(serviceBindingPins=[binding_pin])
    identity = {k: None for k in SERVICE_FIELDS}
    identity.update(schemaVersion='RecoveryNativeServiceIdentity/v1', rehearsalId=REHEARSAL, probeRuntimeProofPin=proof)
    binding = {k: reference(k) for k in ('targetIdentityPin','sourceScopePin','environmentConfigPin',
        'resourcesProofPin','applicationStartPin','role','endpointUrl','dockerPin')}
    identity.update(binding)
    response = {k: None for k in RESULT_FIELDS}
    response.update(schemaVersion='RepositoryLabNativeObserveResult/v1', rehearsalId=REHEARSAL,
                    operationRequestPin=launch['operationRequestPin'], serviceBindingPin=binding_pin)
    if damage == 'foreign-runtime': identity['probeRuntimeProofPin'] = reference('other-proof')
    if damage == 'wrong-binding': identity['targetIdentityPin'] = reference('other-target')
    if damage == 'extra-runtime-field': response['nativeRuntimeProofPin'] = proof
    authenticated = signed_identity(identity) if damage != 'absent-identity' else {}
    if damage:
        with pytest.raises(EnvironmentFailure):
            selected_signing_runtime(response, launch, installation, provision, binding, authenticated)
    else:
        assert 'nativeRuntimeProofPin' not in response and 'probeRuntimeProofPin' not in response
        assert selected_signing_runtime(response, launch, installation, provision, binding, authenticated) == proof


def metadata(uid, gid, mode, inode=2):
    return SimpleNamespace(st_uid=uid, st_gid=gid, st_mode=mode, st_dev=1, st_ino=inode, st_ctime_ns=3)


@pytest.mark.parametrize('damage', [None, 'old-a-owned-0660', 'root-0660', 'parent-group-access', 'replaced-inode'])
def test_socket_custody_metadata_is_distinct_from_positive_a_peer(damage):
    parent = metadata(0, 0, stat.S_IFDIR | 0o700, 1)
    sock = metadata(0, 0, stat.S_IFSOCK | 0o600)
    original = signer_socket_metadata(parent, sock)
    if damage == 'old-a-owned-0660': sock = metadata(24001, 24001, stat.S_IFSOCK | 0o660)
    if damage == 'root-0660': sock.st_mode = stat.S_IFSOCK | 0o660
    if damage == 'parent-group-access': parent.st_mode = stat.S_IFDIR | 0o770
    if damage == 'replaced-inode': sock.st_ino += 1
    if damage:
        with pytest.raises(EnvironmentFailure): signer_socket_metadata(parent, sock, original)
    else: assert signer_socket_metadata(parent, sock, original) == original


def admission_fixture():
    now = datetime.now(timezone.utc)
    stamp = lambda delta: (now + timedelta(seconds=delta)).isoformat().replace('+00:00', 'Z')
    entry = reference('ops/recovery/recovery_native_launcher.py')
    installation = dict(schemaVersion='RepositoryNativeInstallation/v2', root=LAB,
        sourceToolkitPin=reference('toolkit'), pythonPin=reference('python'), dependencyPins=[],
        filePins=[entry] + [reference('ops/recovery/' + n) for n in
            ('repository_native_runtime.py','repository_records.py','recovery_environment_supervisor.py')],
        nativeRuntimeTrustPin=reference('trust'), nativeRuntimeProofPin=reference('proof'))
    launch = dict(operationRequestPin=reference('request'), installationPin=reference('installation'),
                  producerEntryPin=entry, issuedAt=stamp(-20))
    provision = dict(serviceBindingPins=[reference('binding')], producerIdentityPin=reference('producer'),
                     maximumAgeMilliseconds=30000)
    context = SimpleNamespace(launch=launch, launch_pin=reference('launch'), installation=installation,
        provision=provision, proof_pin=installation['nativeRuntimeProofPin'], native_trust={'runtimeRole':'EXECUTOR'},
        proof={'issuedAt':stamp(-20)}, producer_identity={'issuedAt':stamp(-20)},
        grant={'notBefore':stamp(-20)}, lease={'notBefore':stamp(-20)},
        expires_at=stamp(20), deadline=time.monotonic()+20)
    context.installation_command = installation_argv(installation, entry, launch['installationPin'], reference('authority'))
    payload = dict(schemaVersion=ADMISSION_SCHEMA, rehearsalId=REHEARSAL, collectionId='objects', sequence=1,
        phase='BEFORE', operationRequestPin=launch['operationRequestPin'], serviceBindingPin=reference('binding'),
        launchPin=context.launch_pin, installationPin=launch['installationPin'],
        nativeRuntimeTrustPin=installation['nativeRuntimeTrustPin'], nativeRuntimeProofPin=context.proof_pin,
        producerIdentityPin=provision['producerIdentityPin'], invocationPin=reference('invocation'),
        manifestResultPin=reference('manifest'), startedAt=stamp(-3), finishedAt=stamp(-2), issuedAt=stamp(-1), expiresAt=stamp(10))
    call = dict(argv=context.installation_command, commandId='observe-1-before-installation',
        command=wire_canonical(context.installation_command).decode(),
        sourcePins=installation_sources(installation, entry), state='SUCCEEDED', actualExitCode=0,
        startedAt=payload['startedAt'], finishedAt=payload['finishedAt'], resultPin=payload['manifestResultPin'])
    process = dict(call, pythonPin=installation['pythonPin'], nativeRuntimeProofPin=context.proof_pin,
        terminationKind='EXITED', waitStatus=0, descendantState='REAPED', stdoutPin=call['resultPin'])
    return payload, call, process, wire_canonical(installation), b'', context


@pytest.mark.parametrize('damage', [None, 'manifest', 'stderr', 'foreign-role', 'unknown-exit', 'nonzero-wait',
    'command', 'source', 'phase', 'launch', 'proof', 'expired', 'deadline', 'before-lease'])
def test_admission_requires_full_owned_execution_selection_and_manifest(damage):
    payload, call, process, raw, stderr, context = admission_fixture()
    if damage == 'manifest': raw += b'\n'
    if damage == 'stderr': stderr = b'failure'
    if damage == 'foreign-role': context.native_trust['runtimeRole'] = 'VERIFIER'
    if damage == 'unknown-exit': process['terminationKind'] = 'UNKNOWN'; process['actualExitCode'] = None
    if damage == 'nonzero-wait': process['waitStatus'] = 256
    if damage == 'command': process['argv'] = ['true']
    if damage == 'source': process['sourcePins'] = []
    if damage == 'phase': payload['phase'] = 'AFTER'
    if damage == 'launch': payload['launchPin'] = reference('another-launch')
    if damage == 'proof': payload['nativeRuntimeProofPin'] = reference('another-proof')
    if damage == 'expired': payload['expiresAt'] = payload['finishedAt']
    if damage == 'deadline': context.deadline = time.monotonic()-1
    if damage == 'before-lease': context.lease['notBefore'] = payload['issuedAt']
    if damage:
        with pytest.raises(EnvironmentFailure): validate_admission_records(payload, call, process, raw, stderr, context)
    else: validate_admission_records(payload, call, process, raw, stderr, context)


def test_root_and_current_w06_select_same_exact_private_admission_schema():
    value = json.loads((ROOT / 'doc/tasks/20261010-backup-restore-modular-development/backup-server-rehearsal-20261012.json').read_bytes())
    for key in ('nativeLabContinuation20261012','integrationContinuation20261012R3','repairInterfaceAlignment20261012R3',
        'runtimeAndBootstrapContinuation20261012R4','runtimeInstallationContinuation20261012R5',
        'nativeRuntimeContractImplementation20261012R6','repairContinuation20261013R7','repairContinuation20261013R8'):
        value = value[key]
    assert ADMISSION_FIELDS == set(value['contract']['peerInstallationEvidence']['fields'])
    tree = ast.parse((ROOT / 'scripts/recovery_verification/peer_installation.py').read_text(encoding='utf-8'))
    selected = [n for n in tree.body if isinstance(n, ast.Assign) and any(
        isinstance(t, ast.Name) and t.id == 'ADMISSION_FIELDS' for t in n.targets)]
    assert len(selected) == 1 and ADMISSION_FIELDS == set(ast.literal_eval(selected[0].value).split())


def test_whole_selected_graph_includes_trust_catalog_and_rejects_overflow_or_conflict():
    originals = [reference(str(i)) for i in range(4096)]
    assert len(selected_graph_pins([{'nativeFilePins':originals}])) == 4096
    with pytest.raises(EnvironmentFailure, match='NATIVE_GRAPH_LIMIT'):
        selected_graph_pins([originals, reference('new-admission')])
    changed = dict(originals[0], sha256='0'*64)
    with pytest.raises(EnvironmentFailure, match='NATIVE_GRAPH_CONFLICT'): selected_graph_pins([originals, changed])


@pytest.mark.skipif(sys.platform == 'linux', reason='This is the Windows refusal path, not Linux execution acceptance')
def test_real_admit_cli_on_windows_cannot_emit_success_or_manifest():
    command = [sys.executable, str(ROOT / 'ops/recovery/recovery_native_launcher.py'), 'admit-installation',
        '--installation-pin', wire_canonical(reference('installation')).decode(),
        '--authority-pin', wire_canonical(reference('authority')).decode()]
    result = subprocess.run(command, capture_output=True, timeout=10)
    assert result.returncode != 0 and result.stdout == b''
    assert b'NATIVE_ADMISSION_EXECUTOR_ROLE_REQUIRED' in result.stderr
