"""Strict repository records, raw pins and configured authority (v1)."""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time

VERSION = 'nas-repository/1.0.0'


class RepositoryError(Exception):
    def __init__(self, code, *, unknown=False, actual_exit=None):
        super().__init__(code)
        self.code, self.unknown, self.actual_exit = code, unknown, actual_exit


def require(condition, code):
    if not condition:
        raise RepositoryError(code)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def document(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'REPOSITORY_DUPLICATE_JSON_FIELD')
            result[key] = value
        return result
    def nonfinite(_):
        raise RepositoryError('REPOSITORY_NONFINITE_JSON')
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=nonfinite)
    except (UnicodeError, ValueError, RecursionError) as error:
        raise RepositoryError('REPOSITORY_JSON_INVALID') from error


def absolute(value):
    from repository_host_view import resolve
    return resolve(value)


def safe_path(path):
    path = absolute(str(path))
    for part in (path, *path.parents):
        value = part.lstat()
        require(not stat.S_ISLNK(value.st_mode) and not (getattr(value, 'st_file_attributes', 0) & 1024), 'REPOSITORY_REPARSE_REFUSED')
    return path


def signature(value):
    # Windows Python 3.12 path stat reports creation time as ctime, while fstat
    # reports change time. Compare the common native identity fields on handles;
    # retain the pathname ctime comparison separately before/after reading.
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns


def pin_file(path, deadline=None):
    from repository_host_view import logical, original_path
    original = original_path(path) if isinstance(path, Path) else logical(str(path)).as_posix()
    path = safe_path(path)
    before = path.stat()
    require(stat.S_ISREG(before.st_mode), 'REPOSITORY_FILE_REQUIRED')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        require(signature(os.fstat(stream.fileno())) == signature(before), 'REPOSITORY_INPUT_CHANGED')
        while block := stream.read(1024 * 1024):
            if deadline is not None:
                deadline.check()
            digest.update(block)
        require(signature(os.fstat(stream.fileno())) == signature(before), 'REPOSITORY_INPUT_CHANGED')
    after = path.stat()
    require(signature(after) == signature(before) and after.st_ctime_ns == before.st_ctime_ns, 'REPOSITORY_INPUT_CHANGED')
    return {'path': original, 'bytes': before.st_size, 'sha256': digest.hexdigest()}


def validate_pin(pin):
    require(type(pin) is dict and set(pin) == {'path', 'bytes', 'sha256'}, 'REPOSITORY_PIN_INVALID')
    from repository_host_view import logical
    logical(pin['path'])
    require(type(pin['bytes']) is int and pin['bytes'] >= 0 and type(pin['sha256']) is str and re.fullmatch('[0-9a-f]{64}', pin['sha256']), 'REPOSITORY_PIN_INVALID')


def read_pin(pin, limit=16 * 1024 * 1024, deadline=None):
    validate_pin(pin)
    require(pin['bytes'] <= limit, 'REPOSITORY_RECORD_TOO_LARGE')
    require(pin_file(pin['path'], deadline) == pin, 'REPOSITORY_PIN_CHANGED')
    raw = safe_path(pin['path']).read_bytes()
    require(len(raw) == pin['bytes'] and hashlib.sha256(raw).hexdigest() == pin['sha256'], 'REPOSITORY_PIN_CHANGED')
    return raw


def retain_original(path, reference, limit=16 * 1024 * 1024):
    """An archive copy preserves bytes; its Pin never replaces the source Pin."""
    atomic_output_bytes(str(path), read_pin(reference, limit))
    return pin_file(path)


def exact(value, names, schema):
    require(type(value) is dict and set(value) == set(names.split()) and value['schemaVersion'] == schema, 'REPOSITORY_CONFIG_SCHEMA_INVALID')


def timestamp(value):
    require(type(value) is str and value.endswith('Z'), 'REPOSITORY_UTC_REQUIRED')
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as error:
        raise RepositoryError('REPOSITORY_UTC_INVALID') from error
    require(result.tzinfo is not None, 'REPOSITORY_UTC_INVALID')
    return result


def utc():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


class Deadline:
    def __init__(self, milliseconds):
        require(type(milliseconds) is int and 0 < milliseconds <= 7200000, 'REPOSITORY_BUDGET_INVALID')
        self.end = time.monotonic() + milliseconds / 1000
    def check(self):
        require(time.monotonic() < self.end, 'REPOSITORY_BUDGET_EXPIRED')
    def remaining(self):
        self.check()
        return self.end - time.monotonic()


def write_new(path, value):
    path = absolute(str(path))
    safe_path(path.parent)
    raw = canonical(value)
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return pin_file(path)


def atomic_output(path, value):
    atomic_output_bytes(path, canonical(value))


def atomic_output_bytes(path, raw):
    require(type(raw) is bytes, 'REPOSITORY_OUTPUT_BYTES_REQUIRED')
    path = absolute(str(path))
    safe_path(path.parent)
    # Preserve prior outputs; this request owns a fresh output name.
    require(not path.exists(), 'REPOSITORY_OUTPUT_EXISTS')
    temporary = path.with_name(path.name + '.pending')
    with temporary.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    # Hard-link creation is exclusive; replace() would overwrite a concurrent writer.
    os.link(temporary, path)
    temporary.unlink()


def verify_signed(envelope, authority_pins):
    exact(envelope, 'schemaVersion keySha256 payload signature', 'RepositorySignedRecord/v1')
    matches = [pin for pin in authority_pins if pin['sha256'] == envelope['keySha256']]
    require(len(matches) == 1, 'REPOSITORY_AUTHORITY_UNKNOWN')
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature
    try:
        key = load_pem_public_key(read_pin(matches[0], 65536))
        require(isinstance(key, Ed25519PublicKey), 'REPOSITORY_AUTHORITY_KEY_INVALID')
        key.verify(base64.b64decode(envelope['signature'], validate=True), canonical(envelope['payload']))
    except (ValueError, TypeError, InvalidSignature) as error:
        raise RepositoryError('REPOSITORY_SIGNATURE_INVALID') from error
    return envelope['payload']


def signed_pin(pin, authority_pins):
    return verify_signed(document(read_pin(pin)), authority_pins)


class Configuration:
    def __init__(self, config_pin, *, native_implementation=None, host_view_pin=None):
        self.pin = config_pin
        self.native_implementation = native_implementation
        self.value = document(read_pin(config_pin))
        self.native_lab = self.value.get('schemaVersion') == 'RepositoryNativeServiceConfig/v1'
        if self.native_lab:
            require(native_implementation is None and host_view_pin is None,
                    'REPOSITORY_NATIVE_FOREIGN_VIEW_REFUSED')
            from repository_native_lab import configure
            configure(self)
            return
        exact(self.value, 'schemaVersion repositoryId repositoryRoot evidenceRoot schemaPin policyPin authorityKeyPins evidenceKeyPins publisherPin powershellPin installerPin implementationPins captureBinderDependencyPins recoveryApprovalPins hostViewPin', 'RepositoryServiceConfig/v1')
        from repository_host_view import select
        self.active_host_view = self.value['hostViewPin'] if host_view_pin is None else host_view_pin
        select(self.active_host_view)
        if self.value['hostViewPin'] is not None:
            read_pin(self.value['hostViewPin'])
        require(type(self.value['repositoryId']) is str and self.value['repositoryId'], 'REPOSITORY_ID_REQUIRED')
        self.root = safe_path(self.value['repositoryRoot'])
        self.evidence = safe_path(self.value['evidenceRoot'])
        require(self.root.is_dir() and self.evidence.is_dir(), 'REPOSITORY_ROOT_REQUIRED')
        require(self.evidence != self.root and self.root not in self.evidence.parents, 'REPOSITORY_EVIDENCE_ROOT_OVERLAP')
        for name in ('schemaPin', 'policyPin', 'publisherPin', 'powershellPin', 'installerPin'):
            read_pin(self.value[name], 32 * 1024 * 1024)
        self.implementation = self.value['implementationPins']
        require(type(self.implementation) is dict and set(self.implementation) == {'records', 'catalog', 'retention', 'cli', 'nativeBridge', 'installerProgram', 'publisherModule', 'interfaceModule', 'deploymentEvidenceModule', 'publishProgram', 'binding', 'nativePeer', 'nativeReadback', 'captureBinder', 'hostView', 'wslCarrier', 'wslDispatcher'}, 'REPOSITORY_IMPLEMENTATION_PINS_REQUIRED')
        for pin in self.implementation.values():
            read_pin(pin, 32 * 1024 * 1024)
        if self.native_implementation is not None:
            for pin in self.native_implementation.values():
                read_pin(pin, 32 * 1024 * 1024)
        require(type(self.value['captureBinderDependencyPins']) is list and self.value['captureBinderDependencyPins'],
                'REPOSITORY_CAPTURE_BINDER_DEPENDENCIES_REQUIRED')
        for reference in self.value['captureBinderDependencyPins']:
            read_pin(reference, 32 * 1024 * 1024)
        for role, name in (('records', 'repository_records.py'), ('catalog', 'repository_catalog.py'), ('retention', 'repository_retention.py'), ('cli', 'repository_cli.py'), ('nativeBridge', 'repository_native_bridge.py'), ('installerProgram', 'repository_installer.py'), ('publishProgram', 'repository_publish.py'), ('binding', 'repository_binding.py'), ('nativePeer', 'repository_native_peer.py'), ('nativeReadback', 'repository_native_readback.py'), ('hostView', 'repository_host_view.py'), ('wslCarrier', 'repository_wsl_carrier.py'), ('wslDispatcher', 'repository_wsl_dispatcher.py')):
            if native_implementation is not None and role not in native_implementation:
                continue
            if native_implementation is not None:
                reference = native_implementation[role]
                require(all(reference[k] == self.implementation[role][k] for k in ('bytes', 'sha256')),
                        'REPOSITORY_NATIVE_IMPLEMENTATION_CHANGED')
                read_pin(reference, 32 * 1024 * 1024)
                require(absolute(reference['path']) == Path(__file__).absolute().with_name(name),
                        'REPOSITORY_NATIVE_IMPLEMENTATION_LOCATION_CHANGED')
                continue
            require(absolute(self.implementation[role]['path']) == Path(__file__).absolute().with_name(name), 'REPOSITORY_IMPLEMENTATION_LOCATION_CHANGED')
        for role, name in (('publisherModule', 'ReleaseBackupRepository.psm1'), ('interfaceModule', 'ReleaseProductionBackupInterfaces.psm1'), ('deploymentEvidenceModule', 'ReleaseDeploymentEvidence.psm1')):
            if native_implementation is not None:
                continue
            require(absolute(self.implementation[role]['path']) == Path(__file__).absolute().parents[1] / 'release' / 'lib' / name, 'REPOSITORY_IMPLEMENTATION_LOCATION_CHANGED')
        for name in ('authorityKeyPins', 'evidenceKeyPins'):
            require(type(self.value[name]) is list and len(self.value[name]) > 0, 'REPOSITORY_AUTHORITY_REQUIRED')
            for pin in self.value[name]:
                read_pin(pin, 65536)
        require(type(self.value['recoveryApprovalPins']) is list, 'REPOSITORY_RECOVERY_APPROVAL_CONFIG_REQUIRED')
        for reference in self.value['recoveryApprovalPins']:
            read_pin(reference)
        self.schemas = document(read_pin(self.value['schemaPin']))
        self.policy = signed_pin(self.value['policyPin'], self.value['authorityKeyPins'])
        exact(self.policy, 'schemaVersion repositoryId sourceIdentityPin supportedVersionPins supportedToolPins maxChainPoints maxChainAgeSeconds retainNewestPoints minValidFullPoints retentionSeconds legalHoldPointPins copyProtectionPin', 'RepositoryPolicy/v1')
        require(self.policy['repositoryId'] == self.value['repositoryId'], 'REPOSITORY_POLICY_TARGET_MISMATCH')
        for name in ('maxChainPoints', 'maxChainAgeSeconds', 'retainNewestPoints', 'minValidFullPoints', 'retentionSeconds'):
            require(type(self.policy[name]) is int and self.policy[name] > 0, 'REPOSITORY_POLICY_REQUIRED')
        for name in ('supportedVersionPins', 'supportedToolPins', 'legalHoldPointPins'):
            require(type(self.policy[name]) is list, 'REPOSITORY_POLICY_REQUIRED')
            for pin in self.policy[name]:
                read_pin(pin)
        require(self.policy['supportedVersionPins'] and self.policy['supportedToolPins'], 'REPOSITORY_SUPPORTED_VERSIONS_REQUIRED')
        read_pin(self.policy['sourceIdentityPin'])
    def validate(self, value, name):
        from jsonschema import Draft202012Validator, FormatChecker
        schema = {'$ref': '#/$defs/' + name, '$defs': self.schemas['$defs']}
        require(not list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value)), 'REPOSITORY_' + name.upper() + '_SCHEMA_INVALID')
    def current(self):
        if self.native_lab:
            from repository_native_lab import current
            current(self)
            return
        from repository_host_view import current
        current(self.active_host_view)
        read_pin(self.pin)
        read_pin(self.value['policyPin'])
        for field in ('schemaPin', 'publisherPin', 'powershellPin', 'installerPin'):
            read_pin(self.value[field], 64 * 1024 * 1024)
        for pin in self.implementation.values():
            read_pin(pin, 32 * 1024 * 1024)
        if self.native_implementation is not None:
            for pin in self.native_implementation.values():
                read_pin(pin, 32 * 1024 * 1024)
        for reference in self.value['recoveryApprovalPins']:
            read_pin(reference)
        for reference in self.value['captureBinderDependencyPins']:
            read_pin(reference, 32 * 1024 * 1024)
    def request(self, request):
        self.validate(request, 'OperationRequest')
        if self.native_lab:
            from repository_native_lab import lab_scope
            lab_scope(self, request)
        require(request['policyPin'] == self.value['policyPin'], 'REPOSITORY_POLICY_NOT_APPROVED')
        read_pin(request['sourceOrTargetRef'])
        for pin in request['authorizationRefs']:
            read_pin(pin)
        for pin in request['inputPins'].values():
            read_pin(pin)
    def evidence_record(self, pin, schema):
        value = signed_pin(pin, self.value['evidenceKeyPins'])
        require(value['schemaVersion'] == schema and value['repositoryId'] == self.value['repositoryId'], 'REPOSITORY_EVIDENCE_SCOPE_MISMATCH')
        return value
    def copy_protection(self):
        if self.native_lab:
            from repository_native_lab import copy_protection
            return copy_protection(self)
        proof = signed_pin(self.policy['copyProtectionPin'], self.value['authorityKeyPins'])
        exact(proof, 'schemaVersion repositoryId sourceIdentityPin sourceDeletionDenied independentFailureDomain recoveryKeysAvailable validUntil', 'RepositoryCopyProtection/v1')
        require(proof['repositoryId'] == self.value['repositoryId'] and proof['sourceIdentityPin'] == self.policy['sourceIdentityPin'] and all(proof[key] is True for key in ('sourceDeletionDenied', 'independentFailureDomain', 'recoveryKeysAvailable')) and timestamp(proof['validUntil']) > datetime.now(timezone.utc), 'REPOSITORY_COPY_PROTECTION_UNPROVEN')
        read_pin(proof['sourceIdentityPin'])
        return self.policy['copyProtectionPin']
    def authorization(self, request, resource_pin):
        self.current()
        if self.native_lab:
            from repository_native_lab import context, selected_context
            source = document(read_pin(request['sourceOrTargetRef']))
            selected = selected_context(self)
            require(document(read_pin(selected['operationRequestPin'])) == request,
                    'REPOSITORY_LAB_REQUEST_ORIGINAL_CHANGED')
            context(self, source, selected['operationRequestPin'])
        require(request['authorizationRefs'] and request['leaseRef'] is not None, 'REPOSITORY_WRITE_AUTHORITY_REQUIRED')
        now = datetime.now(timezone.utc)
        valid = False
        for pin in request['authorizationRefs']:
            grant = signed_pin(pin, self.value['authorityKeyPins'])
            exact(grant, 'schemaVersion repositoryId operationId actions sourceOrTargetRef policyPin resourcePin notBefore expiresAt leaseRef', 'RepositoryAuthorization/v1')
            require(type(grant['actions']) is list, 'REPOSITORY_AUTHORIZATION_INVALID')
            valid |= (grant['repositoryId'] == self.value['repositoryId'] and grant['operationId'] == request['operationId'] and request['action'] in grant['actions'] and grant['sourceOrTargetRef'] == request['sourceOrTargetRef'] and grant['policyPin'] == request['policyPin'] and grant['resourcePin'] == resource_pin and grant['leaseRef'] == request['leaseRef'] and timestamp(grant['notBefore']) <= now < timestamp(grant['expiresAt']))
        require(valid, 'REPOSITORY_WRITE_NOT_AUTHORIZED')
        lease = signed_pin(request['leaseRef'], self.value['authorityKeyPins'])
        exact(lease, 'schemaVersion repositoryId operationId ownerIdentityPin expiresAt', 'RepositoryLease/v1')
        require(lease['repositoryId'] == self.value['repositoryId'] and lease['operationId'] == request['operationId'] and timestamp(lease['expiresAt']) > now, 'REPOSITORY_LEASE_INVALID')
        read_pin(lease['ownerIdentityPin'])
        return lease


def sign_record(value, private_pin, public_pins):
    from cryptography.hazmat.primitives.serialization import load_pem_private_key, Encoding, PublicFormat
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    key = load_pem_private_key(read_pin(private_pin, 65536), password=None)
    require(isinstance(key, Ed25519PrivateKey), 'REPOSITORY_SIGNING_KEY_INVALID')
    public = key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    sha = hashlib.sha256(public).hexdigest()
    require(any(pin['sha256'] == sha and read_pin(pin, 65536) == public for pin in public_pins), 'REPOSITORY_SIGNING_KEY_NOT_APPROVED')
    return {'schemaVersion': 'RepositorySignedRecord/v1', 'keySha256': sha, 'payload': value, 'signature': base64.b64encode(key.sign(canonical(value))).decode('ascii')}
