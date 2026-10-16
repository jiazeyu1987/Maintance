"""W01 native execution boundary. No host/path discovery, retry, kill or rollback."""
import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import select
import stat
import subprocess
import sys
import time
from contextlib import contextmanager


def selected_lab_authority(args, selected=None):
    need(args.lab_authority_key and args.lab_authority_key_sha256 and args.lab_authority_key_bytes is not None,
         'LAB_INDEPENDENT_AUTHORITY_REQUIRED')
    reference = dict(path=args.lab_authority_key, sha256=args.lab_authority_key_sha256, bytes=args.lab_authority_key_bytes)
    verify(reference)
    if selected is not None:
        need(reference == selected['authorityKeyPin'], 'LAB_INDEPENDENT_AUTHORITY_MISMATCH')
    return reference


def signed_lab_record(reference, authority_pin):
    import base64
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    verify(authority_pin)
    actual, pem = pinned_read(authority_pin['path'], True); need(actual == authority_pin, 'LAB_AUTHORITY_KEY_CHANGED')
    key = load_pem_public_key(pem); need(isinstance(key, Ed25519PublicKey), 'LAB_AUTHORITY_KEY_INVALID')
    envelope = document(reference)
    fields(envelope, 'schemaVersion keySha256 payload signature', 'LAB_ENVELOPE_INVALID')
    need(envelope['schemaVersion'] == 'RepositorySignedRecord/v1' and envelope['keySha256'] == authority_pin['sha256'], 'LAB_SIGNER_MISMATCH')
    key.verify(base64.b64decode(envelope['signature'], validate=True),
               json.dumps(envelope['payload'], ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8'))
    return envelope['payload']


@contextmanager
def installed_repository(installation):
    """Import retained W03 bytes from explicit signed filePins, without search-path changes."""
    import importlib.abc
    import importlib.util
    root = Path('/mnt/intruoyi-data/backup-restore-lab/20261012-w01-w07')
    chosen = installed_repository_modules(installation, pin(Path(__file__).resolve()))
    selected = {}
    retained = []
    for reference in installation['filePins']:
        path = Path(reference['path'])
        if path.suffix == '.py' and path.name.startswith('repository'):
            need(root in path.parents and path.resolve() == path and path.is_file(), 'LAB_SHARED_HELPER_OUTSIDE_SCOPE')
            info = path.stat(); need(info.st_uid == info.st_gid == 0 and stat.S_IMODE(info.st_mode) in (0o600, 0o700), 'LAB_SHARED_HELPER_PRIVATE_REQUIRED')
            actual, raw = pinned_read(path, True); need(actual == reference, 'LAB_SHARED_HELPER_CHANGED')
            retained.append(reference)
            if chosen.get(path.stem) == reference:
                selected[path.stem] = (reference, raw)
    need('repository_native_runtime' in selected and 'repository_records' in selected, 'LAB_SHARED_RUNTIME_HELPER_REQUIRED')

    class Loader(importlib.abc.MetaPathFinder, importlib.abc.Loader):
        def find_spec(self, fullname, path=None, target=None):
            if fullname.startswith('repository'):
                need(fullname in selected, 'LAB_SHARED_IMPORT_NOT_INSTALLED')
                return importlib.util.spec_from_loader(fullname, self)
        def create_module(self, spec):
            return None
        def exec_module(self, module):
            reference, raw = selected[module.__name__]
            verify(reference); module.__file__ = reference['path']; module.__selected_pin__ = reference
            exec(compile(raw, reference['path'], 'exec'), module.__dict__)

    for name, (reference, _) in selected.items():
        if name in sys.modules:
            need(getattr(sys.modules[name], '__selected_pin__', None) == reference, 'LAB_SHARED_IMPORT_ALREADY_UNTRUSTED')
    loader = Loader(); sys.meta_path.insert(0, loader)
    try:
        import importlib
        yield importlib.import_module('repository_native_runtime')
        for reference in retained: verify(reference)
    finally:
        sys.meta_path.remove(loader)


def installed_repository_modules(installation, engine_entry_pin):
    """Select W03 modules adjacent to this exact installed common engine entry."""
    from pathlib import PurePosixPath
    pin_reference(engine_entry_pin)
    need(engine_entry_pin in installation['filePins'], 'LAB_SHARED_ENGINE_NOT_INSTALLED')
    entry = PurePosixPath(engine_entry_pin['path'])
    root = PurePosixPath('/mnt/intruoyi-data/backup-restore-lab/20261012-w01-w07')
    need(root in entry.parents and tuple(entry.parts[-5:]) ==
         ('backend', 'src', 'main', 'resources', 'recovery_control_executor.py'), 'LAB_SHARED_ENGINE_LAYOUT_INVALID')
    module_root = entry.parents[4] / 'ops/recovery'
    selected, paths = {}, set()
    for reference in installation['filePins']:
        pin_reference(reference)
        need(reference['path'] not in paths, 'LAB_INSTALLATION_DUPLICATE')
        paths.add(reference['path'])
        path = PurePosixPath(reference['path'])
        if path.parent == module_root and path.suffix == '.py' and path.name.startswith('repository'):
            need(path.stem not in selected, 'LAB_SHARED_HELPER_AMBIGUOUS')
            selected[path.stem] = reference
    need({'repository_native_runtime', 'repository_records'} <= selected.keys(), 'LAB_SHARED_RUNTIME_HELPER_REQUIRED')
    return selected


def installation_shape(installation):
    version = installation.get('schemaVersion')
    need(version in ('RepositoryNativeInstallation/v1', 'RepositoryNativeInstallation/v2'), 'LAB_INSTALLATION_VERSION_INVALID')
    fields(installation, 'schemaVersion root sourceToolkitPin filePins pythonPin dependencyPins' +
           (' nativeRuntimeTrustPin nativeRuntimeProofPin' if version == 'RepositoryNativeInstallation/v2' else ''), 'LAB_INSTALLATION_FIELDS_INVALID')
    return version


def native_installation(reference, authority_pin, *, deadline=None):
    installation = signed_lab_record(reference, authority_pin)
    need(installation_shape(installation) == 'RepositoryNativeInstallation/v2', 'LAB_NATIVE_INSTALLATION_V2_REQUIRED')
    need(sys.platform == 'linux' and os.geteuid() == os.getegid() == 0, 'LAB_NATIVE_RUNTIME_REQUIRED')
    with installed_repository(installation) as shared:
        verified = shared.verify_native_installation(reference, [authority_pin], deadline=deadline)
        need(verified == installation, 'LAB_SHARED_INSTALLATION_MISMATCH')
    return installation


def native_installation_reader(installation_reference, authority_pin, *, deadline=None):
    # One absolute budget applies to installation admission and every later chunk/range.
    deadline = min(time.monotonic() + 60, deadline) if deadline is not None else time.monotonic() + 60
    installation = native_installation(installation_reference, authority_pin, deadline=deadline)
    trust = signed_lab_record(installation['nativeRuntimeTrustPin'], authority_pin)
    proof_pin = installation['nativeRuntimeProofPin']
    trust_pin = installation['nativeRuntimeTrustPin']
    streamed = ([entry['pin'] for entry in trust['nativeFilePins']] + trust['vendorArtifactPins'] +
                [installation['pythonPin']] + [pin for pin in installation['dependencyPins'] if pin['bytes'] > 134217728])
    def read(reference, *, current_deadline=None):
        role = native_file_role(reference, installation, trust)
        with installed_repository(installation) as shared:
            actual = shared.verify_native_file(reference, trust_pin, proof_pin, role=role,
                                              deadline=min(deadline, current_deadline) if current_deadline is not None else deadline)
            need(actual == reference, 'LAB_NATIVE_MEMBER_CHANGED')
            return actual
    read.streamed = streamed
    return installation, read


def native_file_role(reference, installation, trust):
    """Select a verifier role only from the already authenticated exact membership."""
    if reference in trust['vendorArtifactPins']:
        return 'vendor-artifact'
    if reference == installation['pythonPin'] or (reference in installation['dependencyPins'] and
            str(reference['path']).startswith(installation['root'] + '/') and reference['bytes'] > 134217728):
        need(Path(reference['path']).suffix.lower() not in ('.py', '.pyc', '.json', '.pem', '.key', '.p12', '.pfx'),
             'LAB_NATIVE_INSTALLED_BINARY_NOT_SELECTED')
        return 'installed-binary'
    matches = [entry for entry in trust['nativeFilePins'] if entry['pin'] == reference]
    need(reference in installation['dependencyPins'] and len(matches) == 1, 'LAB_NATIVE_MEMBER_NOT_SELECTED')
    roles = matches[0]['roles']; need(type(roles) is list and bool(roles), 'LAB_NATIVE_MEMBER_ROLE_REQUIRED')
    return roles[0]


def need(value, code):
    if not value:
        raise RuntimeError(code)


def parse(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, 'DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(RuntimeError('INVALID_JSON_NUMBER')))


def pinned_read(path, retain=False, detect_json=False):
    path = Path(path)
    need(path.is_absolute() and path.resolve() == path and path.is_file() and not path.is_symlink(), 'NATIVE_PIN_PATH_INVALID')
    digest = hashlib.sha256(); size = 0; chunks = []; first = None
    flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
    with os.fdopen(os.open(path, flags), 'rb') as stream:
        before = os.fstat(stream.fileno())
        need(stat.S_ISREG(before.st_mode), 'NATIVE_PIN_REGULAR_FILE_REQUIRED')
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            size += len(chunk); digest.update(chunk)
            if detect_json and first is None:
                prefix = chunk.lstrip(b' \t\r\n')
                if prefix: first = prefix[:1]
            if retain:
                need(size <= 16 * 1024 * 1024, 'NATIVE_DOCUMENT_SIZE_LIMIT')
                chunks.append(chunk)
        after = os.fstat(stream.fileno())
    current = path.stat()
    # Windows CRT fstat ctime describes creation; path stat may report NTFS change time.
    # Compare ctime on the retained descriptor, and file identity/size/mtime against the path.
    key = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
    need(key(before) == key(after) == key(current) and before.st_ctime_ns == after.st_ctime_ns and
         (os.name == 'nt' or after.st_ctime_ns == current.st_ctime_ns) and path.resolve() == path and size == after.st_size,
         'NATIVE_PIN_CHANGED_DURING_READ')
    return dict(path=str(path).replace('\\', '/'), bytes=size, sha256=digest.hexdigest()), (first if detect_json else b''.join(chunks))


def json_original(reference):
    pin_reference(reference)
    actual, first = pinned_read(reference['path'], detect_json=True)
    need(actual == reference, 'NATIVE_PIN_CHANGED')
    return first in (b'{', b'[')


def pin(path):
    return pinned_read(path)[0]


def verify(reference):
    pin_reference(reference)
    need(pin(reference['path']) == reference, 'NATIVE_PIN_CHANGED')
    return Path(reference['path'])


def document(reference):
    pin_reference(reference)
    actual, raw = pinned_read(reference['path'], True)
    need(actual == reference, 'NATIVE_PIN_CHANGED')
    return parse(raw)


def fields(value, names, code):
    need(type(value) is dict and set(value) == set(names.split()), code)


def pin_reference(value):
    fields(value, 'path bytes sha256', 'NATIVE_PIN_INVALID')
    need(type(value['path']) is str and type(value['bytes']) is int and value['bytes'] >= 0 and
         type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}', value['sha256']), 'NATIVE_PIN_INVALID')


def caller_timestamp(value):
    need(type(value) is str, 'CALLER_TIMESTAMP_INVALID')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    need(parsed.tzinfo is not None and parsed.utcoffset().total_seconds() == 0, 'CALLER_TIMESTAMP_INVALID')
    return parsed


def native_caller_selection(binding, request, admission=None, host=None):
    """Select signed W05 originals for W06; terminal/identity interpretation stays with W06."""
    originals = binding['independentOriginalPins']
    records = []
    for reference in originals:
        if json_original(reference):
            value = document(reference)
            if type(value) is dict: records.append((reference, value))
    native = []
    for reference, value in records:
        version = value.get('schemaVersion')
        if version == 'RecoveryInvocation/v1' and value.get('processProfile') == 'linux-owned-child-subreaper-v1':
            native.append((reference, value, 'processResultPin', 'RecoveryNativeProcessResult/v1'))
        elif version == 'RecoveryServiceBinding/v2':
            need(value.get('identityProfile') == 'w05-native-readonly-docker-inspect-v1', 'CALLER_NATIVE_IDENTITY_PROFILE_INVALID')
            native.append((reference, value, 'nativeIdentityProofPin', 'RecoveryNativeServiceIdentity/v1'))
    if not native: return
    need(admission is not None and host is not None and request['mode'] == 'REHEARSAL', 'CALLER_NATIVE_PROFILE_LAB_ONLY')
    authority = admission['authorityKeyPin']
    install = signed_lab_record(host['installationManifestPin'], authority)
    need(installation_shape(install) == 'RepositoryNativeInstallation/v2', 'CALLER_NATIVE_INSTALLATION_V2_REQUIRED')
    scope = document(binding['executableScopePin'])
    need(scope.get('schemaVersion') == 'RecoveryExecutableScope/v1' and scope.get('complete') is True and
         scope.get('callerThreadId') == binding['callerThreadId'] and scope.get('producerThreadIds') == binding['producerThreadIds'],
         'CALLER_NATIVE_EXECUTABLE_SCOPE_INVALID')
    sources = scope['sourcePins']
    plan = document(request['inputPins']['restorePlan'])
    for _, value, field, schema in native:
        proof_pin = value.get(field)
        need(proof_pin in originals, 'CALLER_NATIVE_SIGNED_ORIGINAL_NOT_SELECTED')
        proof = signed_lab_record(proof_pin, authority)
        need(proof.get('schemaVersion') == schema and proof.get('rehearsalId') == 'backup-server-rehearsal-20261012-r1',
             'CALLER_NATIVE_RECORD_INVALID')
        need(proof.get('operationId') == request['operationId'] and proof.get('restoreId') == plan['restoreId'] and
             proof.get('targetIdentityPin') == admission['targetIdentityPin'], 'CALLER_NATIVE_CURRENT_OPERATION_MISMATCH')
        if schema == 'RecoveryNativeProcessResult/v1':
            need(all(proof.get(k) == value.get(k) for k in ('operationId', 'restoreId', 'targetIdentityPin', 'recoveryPoint',
                 'stage', 'commandId', 'command', 'argv', 'cwd', 'sourcePins', 'resultPin', 'startedAt', 'finishedAt', 'actualExitCode')) and
                 proof.get('recoveryPoint') == plan['recoveryPoint'], 'CALLER_NATIVE_INVOCATION_MISMATCH')
            need(all(p in sources for p in proof['sourcePins']) and proof['pythonPin'] in sources and
                 proof['supervisorPin'] in sources, 'CALLER_NATIVE_SOURCE_NOT_SELECTED')
        else:
            need(all(proof.get(k) == value.get(k) for k in ('targetIdentityPin', 'sourceScopePin', 'environmentConfigPin',
                 'resourcesProofPin', 'applicationStartPin', 'role', 'endpointUrl', 'dockerPin')) and
                 value.get('sourceScopePin') == binding['sourceScopePin'] and
                 value.get('environmentConfigPin') == request['sourceOrTargetRef'] and
                 value.get('applicationStartPin') == request['inputPins']['applicationStartResult'], 'CALLER_NATIVE_SERVICE_MISMATCH')
            need(proof['probeSourcePin'] in sources and proof['dockerPin'] in sources and
                 all(p in originals for p in proof['invocationPins']), 'CALLER_NATIVE_SOURCE_NOT_SELECTED')


def verification_binding(reference, request_pin, admitted_lab=None):
    """The caller supplies the already admitted dispatch; the binding cannot select one."""
    binding = document(reference)
    need(binding.get('requestPin') == request_pin, 'CALLER_REQUEST_MISMATCH')
    lab = admitted_lab is not None
    fields(binding, 'schemaVersion callerThreadId producerThreadIds requestPin schemaPin sourceScopePin '
           'executableScopePin runTracePin independentOriginalPins validUntil' + (' labAdmissionPin' if lab else ''),
           'CALLER_BINDING_FIELDS_INVALID')
    need(binding['schemaVersion'] == ('RecoveryLabCallerBinding/v1' if lab else 'RecoveryCallerBinding/v1'),
         'CALLER_BINDING_VERSION_INVALID')
    producers = binding['producerThreadIds']
    need(type(binding['callerThreadId']) is str and binding['callerThreadId'].strip() and
         type(producers) is list and bool(producers) and all(type(p) is str and p.strip() for p in producers) and
         len(set(producers)) == len(producers) and binding['callerThreadId'] not in producers, 'CALLER_NOT_INDEPENDENT')
    now = datetime.now(timezone.utc)
    need(caller_timestamp(binding['validUntil']) > now, 'CALLER_BINDING_EXPIRED')
    request = document(request_pin)
    need(request['action'] == 'VERIFY_RECOVERY', 'CALLER_REQUEST_MISMATCH')
    for field in ('schemaPin', 'sourceScopePin', 'executableScopePin', 'runTracePin'):
        verify(binding[field])
    originals = binding['independentOriginalPins']
    need(type(originals) is list and bool(originals), 'CALLER_ORIGINALS_REQUIRED')
    unique = set()
    for original in originals:
        verify(original)
        key = json.dumps(original, sort_keys=True)
        need(key not in unique, 'CALLER_ORIGINAL_DUPLICATE'); unique.add(key)
    if not lab:
        native_caller_selection(binding, request)
        return binding
    dispatch, host, context = admitted_lab
    service = document(dispatch['servicePin'])
    need(request['mode'] == 'REHEARSAL' and context['operationRequestPin'] == request_pin and
         context['authorityKeyPin'] == dispatch['authorityKeyPin'] and
         context['executionHostPin'] == dispatch['executionHostPin'] and
         context['installedClosurePin'] == host['installationManifestPin'] and
         context['labScopePin'] == service['labScopePin'], 'CALLER_LAB_CONTEXT_MISMATCH')
    need(caller_timestamp(context['issuedAt']) <= now < caller_timestamp(context['expiresAt']), 'LAB_AUTHORITY_EXPIRED')
    need(dispatch['labContextPin'] not in originals, 'CALLER_LAB_CONTEXT_MUST_BE_OUT_OF_BAND')
    admission_pin = binding['labAdmissionPin']; admission = document(admission_pin)
    fields(admission, 'schemaVersion authorityKeyPin repositoryEvidenceKeyPin copyProtectionEvidenceKeyPins labScopePin sourceIdentityPin '
           'executionHostPin installedClosurePin targetIdentityPin mode validUntil', 'CALLER_LAB_ADMISSION_FIELDS_INVALID')
    need(admission['schemaVersion'] == 'RecoveryLabAdmission/v2', 'CALLER_LAB_ADMISSION_VERSION_INVALID')
    need(admission['mode'] == 'REHEARSAL' and caller_timestamp(admission['validUntil']) > now,
         'CALLER_LAB_ADMISSION_EXPIRED_OR_MODE_INVALID')
    need(all(admission[k] == context[k] for k in ('authorityKeyPin', 'labScopePin', 'sourceIdentityPin',
                                                'executionHostPin', 'installedClosurePin')), 'CALLER_LAB_ADMISSION_MISMATCH')
    copy_keys = admission['copyProtectionEvidenceKeyPins']
    need(type(copy_keys) is list and bool(copy_keys), 'CALLER_LAB_COPY_KEYS_REQUIRED')
    key_pins, key_hashes = set(), set()
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    for key in copy_keys:
        pin_reference(key)
        encoded = json.dumps(key, sort_keys=True)
        need(encoded not in key_pins and key['sha256'] not in key_hashes, 'CALLER_LAB_COPY_KEYS_DUPLICATE')
        key_pins.add(encoded); key_hashes.add(key['sha256'])
        need(key in originals, 'CALLER_LAB_COPY_KEY_NOT_SELECTED')
        need(key['bytes'] <= 65536, 'CALLER_LAB_COPY_KEY_INVALID')
        verify(key)
        actual_key, raw_key = pinned_read(key['path'], True)
        need(actual_key == key, 'NATIVE_PIN_CHANGED')
        try:
            public_key = load_pem_public_key(raw_key)
        except (ValueError, TypeError) as error:
            raise RuntimeError('CALLER_LAB_COPY_KEY_INVALID') from error
        need(isinstance(public_key, Ed25519PublicKey), 'CALLER_LAB_COPY_KEY_INVALID')
    policy = document(request['policyPin'])
    fields(policy, 'schemaVersion maxAgeMilliseconds rtoObjectiveMilliseconds rpoObjectiveMilliseconds '
           'recoveryTargetPin verificationTargetPin dataBaselinePin dataObservationPin protectionBeforePin protectionAfterPin '
           'playwrightObservationPin timingObservationPin requiredUserPaths protectedScopes requireDeletedReferenceObjects '
           'derivedBaselinePin controlledEligibilityPin', 'CALLER_LAB_POLICY_FIELDS_INVALID')
    need(policy['schemaVersion'] == 'RecoveryVerificationPolicy/v2', 'CALLER_LAB_POLICY_INVALID')
    need(type(policy['maxAgeMilliseconds']) is int and policy['maxAgeMilliseconds'] >= 1 and
         all(policy[k] is None or (type(policy[k]) is int and policy[k] >= 0)
             for k in ('rtoObjectiveMilliseconds', 'rpoObjectiveMilliseconds')), 'CALLER_LAB_POLICY_INVALID')
    need(policy['controlledEligibilityPin'] is None, 'CALLER_LAB_CONTROLLED_ELIGIBILITY_PROHIBITED')
    target = document(policy['recoveryTargetPin'])
    fields(target, 'schemaVersion targetId targetIdentityPin resourcesProofPin isolationProofPin versionPins configurationPin secretRefs sideEffectIsolationPin leaseRef modePreconditionsPin', 'CALLER_LAB_TARGET_INVALID')
    need(target.get('schemaVersion') == 'RecoveryTarget/v1', 'CALLER_LAB_TARGET_INVALID')
    verification_target = document(policy['verificationTargetPin'])
    fields(verification_target, 'schemaVersion targetIdentityPin targetId environment databaseId frontendOrigin objectBindingPin', 'CALLER_LAB_TARGET_INVALID')
    need(verification_target['schemaVersion'] == 'RecoveryVerificationTarget/v1', 'CALLER_LAB_TARGET_INVALID')
    restored = document(request['inputPins']['restoreExecutionResult'])
    need(target.get('targetIdentityPin') == restored.get('targetIdentityPin') == verification_target['targetIdentityPin'] == admission['targetIdentityPin'] and
         verification_target['targetId'] == target['targetId'] and verification_target['environment'] == 'ISOLATED' and
         target['configurationPin'] == request['sourceOrTargetRef'], 'CALLER_LAB_TARGET_MISMATCH')
    need(admission['repositoryEvidenceKeyPin'] in service['evidenceKeyPins'], 'CALLER_LAB_EVIDENCE_KEY_NOT_SELECTED')
    source = document(binding['sourceScopePin'])
    need(source.get('schemaVersion') == 'RecoverySourceScope/v1' and source.get('sourceIdentityPin') == context['sourceIdentityPin'],
         'CALLER_LAB_SOURCE_MISMATCH')
    configuration = document(request['sourceOrTargetRef'])
    need(configuration.get('schemaVersion') == 'RecoveryEnvironmentConfig/v1' and
         configuration.get('sourceScopePin') == binding['sourceScopePin'], 'CALLER_LAB_SOURCE_MISMATCH')
    need(admission_pin in originals, 'CALLER_LAB_ADMISSION_NOT_SELECTED')
    need(all(admission[k] in originals for k in ('authorityKeyPin', 'repositoryEvidenceKeyPin', 'labScopePin',
                                                'sourceIdentityPin', 'executionHostPin', 'installedClosurePin',
                                                'targetIdentityPin')), 'CALLER_LAB_ORIGINAL_NOT_SELECTED')
    native_caller_selection(binding, request, admission, host)
    return binding


def namespace_record(value, host):
    """Pure validation; no namespace discovery or privileged action."""
    fields(value, 'schemaVersion taskId hostId bootId uid daemon namespaces', 'NAMESPACE_REGISTRATION_FIELDS_INVALID')
    need(value['schemaVersion'] == 'RecoveryControlNamespaceRegistration/v1' and
         value['taskId'] == '20261010-backup-restore-modular-development', 'NAMESPACE_REGISTRATION_VERSION_INVALID')
    need(host['hostOs'] == 'Linux' and type(value['uid']) is int and value['uid'] == host['uid'] == 0 and
         all(value[k] == host[k] for k in ('hostId', 'bootId')), 'NAMESPACE_HOST_IDENTITY_MISMATCH')
    daemon = value['daemon']
    fields(daemon, 'pid startTimeTicks executablePin', 'NAMESPACE_DAEMON_FIELDS_INVALID')
    need(type(daemon['pid']) is int and daemon['pid'] > 1 and
         type(daemon['startTimeTicks']) is int and daemon['startTimeTicks'] > 0, 'NAMESPACE_DAEMON_IDENTITY_REQUIRED')
    pin_reference(daemon['executablePin'])
    need(type(daemon['executablePin']) is dict and Path(daemon['executablePin'].get('path', '')).name == 'dockerd',
         'NAMESPACE_DOCKER_DAEMON_REQUIRED')
    fields(value['namespaces'], 'net mount', 'NAMESPACE_SET_INVALID')
    for key, filename in (('net', 'net'), ('mount', 'mnt')):
        namespace = value['namespaces'][key]
        fields(namespace, 'path device inode', 'NAMESPACE_FD_IDENTITY_FIELDS_INVALID')
        need(namespace['path'] == '/proc/%d/ns/%s' % (daemon['pid'], filename) and
             type(namespace['device']) is int and namespace['device'] >= 0 and
             type(namespace['inode']) is int and namespace['inode'] > 0, 'NAMESPACE_FD_IDENTITY_REQUIRED')
    return value


def execution_profile(value, host):
    fields(value, 'schemaVersion transport hostOs hostId bootId uid sourceProfilePin pythonPin dispatcherPin scriptPin '
           'workingDirectory evidenceRoot launcherPin launcherArguments environment resourceObserverPin namespaceRegistrationPin',
           'NATIVE_PROFILE_FIELDS_INVALID')
    need(value['schemaVersion'] == 'RecoveryControlExecutionHost/v2', 'NATIVE_PROFILE_VERSION_INVALID')
    need(value['transport'] in ('LOCAL', 'WSL'), 'NATIVE_TRANSPORT_INVALID')
    if value['transport'] == 'WSL':
        need(host['hostOs'] == 'Linux' and value['launcherArguments'] ==
             ['--distribution', 'br20261010-w01w07-native', '--user', 'root', '--exec'], 'NATIVE_FIXED_WSL_REQUIRED')
    else:
        need(value['launcherPin'] is None and value['launcherArguments'] == [], 'NATIVE_LOCAL_LAUNCHER_FIELDS_INVALID')
    need(all(value[key] == selected for key, selected in host.items()), 'NATIVE_HOST_IDENTITY_MISMATCH')
    need(type(value['environment']) is dict and bool(value['environment']) and
         all(type(k) is str and type(v) is str for k, v in value['environment'].items()), 'NATIVE_ENVIRONMENT_REQUIRED')
    if host['hostOs'] == 'Linux':
        need(type(value['uid']) is int and value['uid'] == 0, 'NAMESPACE_NATIVE_ROOT_REQUIRED')
        namespace_record(document(value['namespaceRegistrationPin']), host)
    else:
        need(value['namespaceRegistrationPin'] is None, 'WINDOWS_NAMESPACE_REGISTRATION_REFUSED')
    return value


def linux_start_ticks(raw, expected_pid):
    # comm may contain spaces and ')'; field 22 starts at offset 19 after comm.
    suffix = raw[raw.rfind(')') + 2:].split()
    need(raw.split(' ', 1)[0] == str(expected_pid) and len(suffix) > 19 and
         suffix[0] not in ('Z', 'X', 'x') and suffix[19].isdigit(), 'NAMESPACE_DAEMON_STAT_INVALID')
    return int(suffix[19])


class NativeNamespace:
    """Retain daemon/proc/namespace FDs; one trusted same-daemon join, no PID argument."""
    def __init__(self, profile):
        need(sys.platform == 'linux' and os.geteuid() == 0 and hasattr(os, 'setns') and
             hasattr(os, 'pidfd_open'), 'NAMESPACE_NATIVE_PREREQUISITE_REQUIRED')
        self.profile = profile; self.host = identity()
        self.reference = profile['namespaceRegistrationPin']
        self.record = namespace_record(document(self.reference), self.host)
        source = document(profile['sourceProfilePin'])
        need(source.get('schemaVersion') == 'RecoveryLocalEnvironmentRegistration/v1' and
             source.get('usableForExecution') is True and
             source.get('host', {}).get('namespaceRegistrationPin') == self.reference and
             source.get('host', {}).get('selectedExecutionHost') is not None,
             'NAMESPACE_REGISTRATION_NOT_SOURCE_ANCHORED')
        self.fds = {}; self.proc_fd = None; self.pid_fd = None; self.joined = False
        self.pid = self.record['daemon']['pid']
        try:
            need(len(list(Path('/proc/self/task').iterdir())) == 1, 'NAMESPACE_SINGLE_THREAD_REQUIRED')
            self.proc_fd = os.open('/proc/%d' % self.pid, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)
            self.pid_fd = os.pidfd_open(self.pid, 0)
            self.check_daemon()
            import fcntl
            for key, filename, namespace_type in (('net', 'net', os.CLONE_NEWNET), ('mount', 'mnt', os.CLONE_NEWNS)):
                fd = os.open('ns/' + filename, os.O_RDONLY | os.O_CLOEXEC, dir_fd=self.proc_fd)
                self.fds[key] = fd
                need(fcntl.ioctl(fd, 0xb703) == namespace_type, 'NAMESPACE_FD_TYPE_MISMATCH')  # NS_GET_NSTYPE
                actual = os.fstat(fd); selected = self.record['namespaces'][key]
                need((actual.st_dev, actual.st_ino) == (selected['device'], selected['inode']), 'NAMESPACE_OPEN_FD_IDENTITY_MISMATCH')
                current = os.stat('/proc/self/ns/' + filename)
                need((current.st_dev, current.st_ino) != (actual.st_dev, actual.st_ino), 'NAMESPACE_NOT_PRIVATE_FROM_LAUNCHER')
            self.recheck(False)
        except BaseException:
            self.close()
            raise

    def proc_read(self, name):
        fd = os.open(name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=self.proc_fd)
        with os.fdopen(fd, 'r', encoding='utf-8') as stream:
            raw = stream.read(65537)
        need(len(raw) <= 65536, 'NAMESPACE_PROC_RECORD_TOO_LARGE')
        return raw

    def check_daemon(self):
        daemon = self.record['daemon']
        need(not select.select([self.pid_fd], [], [], 0)[0], 'NAMESPACE_DAEMON_EXITED')
        need(linux_start_ticks(self.proc_read('stat'), self.pid) == daemon['startTimeTicks'], 'NAMESPACE_DAEMON_START_CHANGED')
        need(linux_start_ticks(Path('/proc/%d/stat' % self.pid).read_text(), self.pid) == daemon['startTimeTicks'], 'NAMESPACE_DAEMON_PID_REUSED')
        need(re.search(r'^Uid:\s+0\s+0\s+0\s+0\s*$', self.proc_read('status'), re.M), 'NAMESPACE_DAEMON_ROOT_REQUIRED')
        executable = os.readlink('exe', dir_fd=self.proc_fd)
        need(executable == daemon['executablePin']['path'], 'NAMESPACE_DAEMON_EXECUTABLE_MISMATCH')
        verify(daemon['executablePin'])
        actual = os.stat('exe', dir_fd=self.proc_fd); selected = os.stat(executable)
        need((actual.st_dev, actual.st_ino) == (selected.st_dev, selected.st_ino), 'NAMESPACE_DAEMON_EXECUTABLE_REPLACED')

    def recheck(self, joined):
        need(identity() == self.host, 'NAMESPACE_HOST_OR_BOOT_CHANGED')
        need(document(self.reference) == self.record, 'NAMESPACE_REGISTRATION_CHANGED')
        source = document(self.profile['sourceProfilePin'])
        need(source.get('host', {}).get('namespaceRegistrationPin') == self.reference and
             source.get('usableForExecution') is True, 'NAMESPACE_SOURCE_ANCHOR_CHANGED')
        self.check_daemon()
        for key, filename in (('net', 'net'), ('mount', 'mnt')):
            selected = self.record['namespaces'][key]; expected = (selected['device'], selected['inode'])
            observations = (os.fstat(self.fds[key]), os.stat('ns/' + filename, dir_fd=self.proc_fd), os.stat(selected['path']))
            need(all((v.st_dev, v.st_ino) == expected for v in observations), 'NAMESPACE_DAEMON_FD_OR_PATH_CHANGED')
            if joined:
                current = os.stat('/proc/self/ns/' + filename)
                need((current.st_dev, current.st_ino) == expected, 'NAMESPACE_JOIN_NOT_CONFIRMED')
        verify(self.profile['pythonPin']); verify(self.profile['dispatcherPin'])
        running = os.stat('/proc/self/exe'); selected_python = os.stat(self.profile['pythonPin']['path'])
        need((running.st_dev, running.st_ino) == (selected_python.st_dev, selected_python.st_ino),
             'NAMESPACE_RUNNING_PYTHON_IDENTITY_MISMATCH')

    def enter(self):
        need(not self.joined, 'NAMESPACE_ALREADY_JOINED')
        self.recheck(False)
        os.setns(self.fds['net'], os.CLONE_NEWNET)
        os.setns(self.fds['mount'], os.CLONE_NEWNS)
        self.joined = True
        self.recheck(True)
        return dict(schemaVersion='RecoveryControlNamespaceEntry/v1', namespaceRegistrationPin=self.reference,
                    hostId=self.host['hostId'], bootId=self.host['bootId'], daemon=self.record['daemon'],
                    namespaces=self.record['namespaces'], enteredMonotonicNs=time.monotonic_ns())

    def close(self):
        for fd in [*self.fds.values(), self.proc_fd, self.pid_fd]:
            if fd is not None:
                os.close(fd)
        self.fds = {}; self.proc_fd = None; self.pid_fd = None


def write(path, value):
    path = Path(path); temporary = path.with_name(path.name + '.tmp')
    with temporary.open('wb') as stream:
        if os.name == 'posix': os.chmod(temporary, 0o600)
        stream.write(json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode('ascii'))
        stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, path)
    return pin(path)


def identity():
    if sys.platform == 'linux':
        return dict(hostOs='Linux', hostId=Path('/etc/machine-id').read_text().strip(),
                    bootId=Path('/proc/sys/kernel/random/boot_id').read_text().strip(), uid=os.geteuid())
    need(os.name == 'nt', 'NATIVE_HOST_UNSUPPORTED')
    import winreg
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Cryptography', 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
        host = winreg.QueryValueEx(key, 'MachineGuid')[0]
    class Day(ctypes.Structure):
        _fields_ = [('boot', ctypes.c_longlong), ('current', ctypes.c_longlong), ('bias', ctypes.c_longlong),
                    ('zone', ctypes.c_ulong), ('reserved', ctypes.c_ulong), ('boot_bias', ctypes.c_ulonglong), ('sleep_bias', ctypes.c_ulonglong)]
    day = Day()
    need(ctypes.windll.ntdll.NtQuerySystemInformation(3, ctypes.byref(day), ctypes.sizeof(day), None) == 0, 'WINDOWS_BOOT_IDENTITY_UNAVAILABLE')
    return dict(hostOs='Windows', hostId=host, bootId=str(day.boot), uid=None)


def process_start(process, boot):
    if os.name == 'posix':
        raw = Path('/proc/%d/stat' % process.pid).read_text()
        return 'linux:' + boot + ':' + raw[raw.rfind(')') + 2:].split()[19]
    class FileTime(ctypes.Structure):
        _fields_ = [('low', ctypes.c_uint32), ('high', ctypes.c_uint32)]
    values = [FileTime() for _ in range(4)]
    need(ctypes.windll.kernel32.GetProcessTimes(ctypes.c_void_p(int(process._handle)), *(ctypes.byref(v) for v in values)), 'PROCESS_START_IDENTITY_UNAVAILABLE')
    return 'windows:' + str((values[0].high << 32) | values[0].low)


def sample(phase, stdout, stderr):
    return dict(monotonicNs=time.monotonic_ns(), wallNs=time.time_ns(), phase=phase,
                bytes=stdout.stat().st_size + stderr.stat().st_size, count=0,
                cpuNanoseconds=None, residentBytes=None, stopWrites=False)


def run_owner(python_pin, program_pin, configuration_pin, request_pin, output, *, environment,
              working_directory, deadline_milliseconds):
    """Run one configured owner CLI and retain its actual terminal and streams.

    This is the single-operator entry. It does not consume lab signatures,
    participant identities, installation receipts or an operation authority DAG.
    Owner CLIs remain responsible for consistent capture and safe target writes.
    A deadline observation never launches another process or kills this one.
    """
    dispatch = {'started': False}
    try:
        return _run_owner(python_pin, program_pin, configuration_pin, request_pin, output,
            environment=environment, working_directory=working_directory,
            deadline_milliseconds=deadline_milliseconds, dispatch=dispatch)
    except Exception as error:
        error.owner_dispatched = dispatch['started']
        raise


def _run_owner(python_pin, program_pin, configuration_pin, request_pin, output, *, environment,
               working_directory, deadline_milliseconds, dispatch):
    for reference in (python_pin, program_pin, configuration_pin, request_pin):
        verify(reference)
    request = document(request_pin)
    need(type(deadline_milliseconds) is int and deadline_milliseconds > 0,
         'ORIGINAL_DEADLINE_REQUIRED')
    root = Path(output).parent
    need(root.is_absolute() and root.resolve() == root and root.is_dir() and not Path(output).exists(),
         'NATIVE_OUTPUT_SCOPE_INVALID')
    need(type(environment) is dict and all(type(k) is str and type(v) is str for k, v in environment.items()),
         'NATIVE_ENVIRONMENT_REQUIRED')
    argv = [python_pin['path'], program_pin['path'], '--configuration', configuration_pin['path'],
            '--request', request_pin['path'], '--output', str(output)]
    intent = write(root / 'native-intent.json', dict(operationId=request['operationId'],
        requestId=request['operationId'], requestPin=request_pin, configurationPin=configuration_pin,
        pythonPin=python_pin, programPin=program_pin, argv=argv))
    deadline = time.monotonic() + deadline_milliseconds / 1000
    timed_out = False
    with (root / 'native-stdout').open('xb') as stdout, (root / 'native-stderr').open('xb') as stderr:
        if os.name == 'posix':
            os.chmod(stdout.name, 0o600); os.chmod(stderr.name, 0o600)
        process = subprocess.Popen(argv, cwd=working_directory, env=environment,
            stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, start_new_session=os.name == 'posix')
        dispatch['started'] = True
        write(root / 'native-process.json', dict(operationId=request['operationId'],
            requestId=request['operationId'], intentPin=intent, pid=process.pid))
        while True:
            try:
                code = process.wait(timeout=.2)
                break
            except subprocess.TimeoutExpired:
                if not timed_out and time.monotonic() >= deadline:
                    timed_out = True
                    write(root / 'timeout-observation.json', dict(operationId=request['operationId'],
                        requestId=request['operationId'], originalOperationOnly=True, retryAllowed=False))
    terminal = dict(operationId=request['operationId'], requestId=request['operationId'],
        requestPin=request_pin, intentPin=intent, pid=process.pid, actualExitCode=code,
        timedOut=timed_out, stdoutPin=pin(root / 'native-stdout'), stderrPin=pin(root / 'native-stderr'),
        resultPin=pin(output) if Path(output).is_file() else None)
    write(root / 'native-original-exit.json', terminal)
    return terminal


def run(args):
    lab_admission = None
    native_launch_reference = None
    if args.lab_dispatch:
        need(args.profile is None and args.profile_sha256 is None, 'AMBIGUOUS_EXECUTION_PROFILE')
        import importlib.util
        helper = Path(__file__).resolve().with_name('recovery_control_lab.py')
        profile_pin = pin(args.lab_dispatch)
        need(profile_pin['sha256'] == args.lab_dispatch_sha256, 'LAB_DISPATCH_CHANGED')
        selected = document(profile_pin)
        fields(selected, 'schemaVersion executionHostPin servicePin programPin labContextPin authorityKeyPin', 'LAB_DISPATCH_FIELDS_INVALID')
        need(selected['schemaVersion'] == 'RecoveryControlBackupLabDispatch/v1', 'LAB_DISPATCH_VERSION_INVALID')
        authority_pin = selected_lab_authority(args, selected)
        # Authenticate the helper bytes before importing any of its code.
        import base64
        from cryptography.hazmat.primitives.serialization import load_pem_public_key
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        key_pin = authority_pin
        key = load_pem_public_key(pinned_read(key_pin['path'], True)[1])
        need(isinstance(key, Ed25519PublicKey), 'LAB_AUTHORITY_KEY_INVALID')
        host = document(selected['executionHostPin']); signed_install = document(host['installationManifestPin'])
        fields(signed_install, 'schemaVersion keySha256 payload signature', 'LAB_INSTALLATION_ENVELOPE_INVALID')
        need(signed_install['schemaVersion'] == 'RepositorySignedRecord/v1' and signed_install['keySha256'] == key_pin['sha256'], 'LAB_INSTALLATION_SIGNER_INVALID')
        key.verify(base64.b64decode(signed_install['signature'], validate=True), json.dumps(signed_install['payload'], ensure_ascii=False,
                   sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8'))
        helper_pin = pin(helper)
        need(helper_pin in signed_install['payload']['filePins'], 'LAB_AUTHORITY_HELPER_NOT_INSTALLED')
        raw_helper = pinned_read(helper, True)[1]
        need(pin(helper) == helper_pin, 'LAB_AUTHORITY_HELPER_CHANGED')
        # Execute the retained verified bytes, avoiding an import-time reopen race.
        import types
        module = types.ModuleType('recovery_control_lab'); module.__file__ = str(helper)
        exec(compile(raw_helper, str(helper), 'exec'), module.__dict__)
        request_pin = pin(args.request); need(request_pin['sha256'] == args.request_sha256, 'NATIVE_REQUEST_CHANGED')
        caller_reference = None
        if args.verification_binding:
            need(args.verification_binding_sha256 and args.verification_binding_bytes is not None, 'OPERATION_CALLER_BINDING_REQUIRED')
            caller_reference = dict(path=args.verification_binding, sha256=args.verification_binding_sha256, bytes=args.verification_binding_bytes)
        if args.lab_native_launch:
            need(args.lab_native_launch_sha256 and args.lab_native_launch_bytes is not None, 'LAB_NATIVE_LAUNCH_PIN_REQUIRED')
            native_launch_reference = dict(path=args.lab_native_launch, sha256=args.lab_native_launch_sha256, bytes=args.lab_native_launch_bytes)
        else:
            need(args.lab_native_launch_sha256 is None and args.lab_native_launch_bytes is None, 'LAB_NATIVE_LAUNCH_PIN_REQUIRED')
        lab_admission = lambda: module.admit(sys.modules[__name__], profile_pin, request_pin, Path(__file__).resolve(),
                                           authority_pin=authority_pin, caller_binding=caller_reference, native_launch=native_launch_reference)
        dispatch, profile, context = lab_admission()
        profile = dict(profile, scriptPin=dispatch['programPin'])
    else:
        need(args.lab_dispatch_sha256 is None, 'LAB_DISPATCH_REQUIRED')
        need(args.lab_authority_key is None and args.lab_authority_key_sha256 is None and args.lab_authority_key_bytes is None,
             'UNEXPECTED_LAB_AUTHORITY')
        need(args.lab_native_launch is None and args.lab_native_launch_sha256 is None and args.lab_native_launch_bytes is None,
             'UNEXPECTED_LAB_NATIVE_LAUNCH')
        profile_pin = pin(args.profile)
        need(profile_pin['sha256'] == args.profile_sha256, 'NATIVE_PROFILE_CHANGED')
    actual_host = identity()
    if lab_admission is None:
        profile = execution_profile(document(profile_pin), actual_host)
    verify(profile['sourceProfilePin']); verify(profile['pythonPin']); verify(profile['dispatcherPin']); verify(profile['scriptPin'])
    source_profile = document(profile['sourceProfilePin'])
    if source_profile.get('schemaVersion') == 'RecoveryLocalEnvironmentRegistration/v1':
        need(source_profile.get('usableForExecution') is True and
             source_profile.get('host', {}).get('selectedExecutionHost') is not None, 'W05_EXECUTION_ENVIRONMENT_NOT_USABLE')
    need(Path(sys.executable).resolve() == Path(profile['pythonPin']['path']) and
         Path(__file__).resolve() == Path(profile['dispatcherPin']['path']), 'NATIVE_EXECUTABLE_IDENTITY_MISMATCH')
    namespace = None; namespace_entry = None
    if actual_host['hostOs'] == 'Linux' and lab_admission is None:
        namespace = NativeNamespace(profile)
        namespace_entry = namespace.enter()
    elif lab_admission is None:
        need(profile['namespaceRegistrationPin'] is None, 'WINDOWS_NAMESPACE_REGISTRATION_REFUSED')
    request_pin = pin(args.request); need(request_pin['sha256'] == args.request_sha256, 'NATIVE_REQUEST_CHANGED')
    request = document(request_pin); root = Path(args.output).parent
    need(profile['resourceObserverPin'] is not None or request['action'] not in
         ('BACKUP_FULL', 'BACKUP_INCREMENTAL', 'RETENTION_EXECUTE', 'PREPARE_TARGET', 'RESTORE_EXECUTE',
          'START_APPLICATION', 'REHEARSAL', 'CONTROLLED_CUTOVER'), 'NATIVE_RESOURCE_OBSERVER_REQUIRED')
    need(root.is_absolute() and root.resolve() == root and root.is_dir() and
         root.parent.parent == Path(profile['evidenceRoot']) and not Path(args.output).exists(), 'NATIVE_OUTPUT_SCOPE_INVALID')
    if os.name == 'posix':
        need(root.stat().st_uid == os.geteuid() and root.stat().st_mode & 0o077 == 0, 'PRIVATE_NATIVE_EVIDENCE_REQUIRED')
    environment = dict(profile['environment'])
    if lab_admission is not None:
        environment['INTRUOYI_BACKUP_LAB_CONTEXT_PATH'] = dispatch['labContextPin']['path']
        environment['INTRUOYI_BACKUP_LAB_CONTEXT_SHA256'] = dispatch['labContextPin']['sha256']
        environment['INTRUOYI_REPOSITORY_LAB_CONTEXT_PATH'] = dispatch['labContextPin']['path']
        environment['INTRUOYI_REPOSITORY_LAB_CONTEXT_SHA256'] = dispatch['labContextPin']['sha256']
        if native_launch_reference is not None:
            # Explicit controller selection; never derive this Pin from worker/request claims.
            environment['RECOVERY_VERIFICATION_NATIVE_LAUNCH_PIN'] = json.dumps(native_launch_reference, sort_keys=True, separators=(',', ':'))
    if request['action'] == 'VERIFY_RECOVERY':
        need(args.verification_binding and args.verification_binding_sha256 and args.verification_binding_bytes is not None, 'OPERATION_CALLER_BINDING_REQUIRED')
        binding_reference = dict(path=args.verification_binding, bytes=args.verification_binding_bytes, sha256=args.verification_binding_sha256)
        verification_binding(binding_reference, request_pin, None if lab_admission is None else (dispatch, profile, context))
        environment['RECOVERY_VERIFICATION_TRUST_PIN'] = json.dumps(binding_reference, sort_keys=True, separators=(',', ':'))
    else:
        need(args.verification_binding is None, 'UNEXPECTED_VERIFICATION_BINDING')
    stdout = root / 'native-stdout'; stderr = root / 'native-stderr'
    clock = dict(hostId=actual_host['hostId'], bootId=actual_host['bootId'])
    envelope = dict(schemaVersion='recovery-execution-evidence/v1', operationId=request['operationId'], attemptId=args.attempt,
        observerEpoch=args.epoch, clockDomain=clock, samples=[], exits=dict(executor=None, runner=None, test=None),
        timedOut=False, timeoutLayer=None, complete=False, processTerminal=None, resourceTerminal=None,
        streamRefs=dict(stdout=None, stderr=None), originalPins=[request_pin, profile_pin, profile['sourceProfilePin']])
    started = time.monotonic_ns(); deadline = started + request['deadlineMilliseconds'] * 1000000
    process = None; start_id = None; resource_pin = None
    if namespace_entry is not None:
        namespace_entry.update(operationId=request['operationId'], requestId=request['requestId'],
                               requestPin=request_pin, profilePin=profile_pin, attemptId=args.attempt)
        envelope['originalPins'].append(write(root / 'namespace-entry.json', namespace_entry))
    with stdout.open('xb') as out, stderr.open('xb') as err:
        if os.name == 'posix': os.chmod(stdout, 0o600); os.chmod(stderr, 0o600)
        envelope['samples'].append(sample('DISPATCH', stdout, stderr))
        intent_pin = write(root / 'native-intent.json', dict(schemaVersion='RecoveryControlNativeIntent/v1',
            operationId=request['operationId'], requestId=request['requestId'], requestPin=request_pin,
            attemptId=args.attempt, observerEpoch=args.epoch, clockDomain=clock, profilePin=profile_pin,
            pythonPin=profile['pythonPin'], scriptPin=profile['scriptPin'], startedMonotonicNs=started))
        envelope['originalPins'].append(intent_pin)
        if namespace is not None:
            namespace.recheck(True)
        for reference in (profile['scriptPin'], profile['dispatcherPin'], profile['sourceProfilePin'], profile_pin, request_pin):
            verify(reference)
        if lab_admission is not None:
            dispatch, admitted_host, context = lab_admission()
        if request['action'] == 'VERIFY_RECOVERY':
            verification_binding(binding_reference, request_pin, None if lab_admission is None else (dispatch, admitted_host, context))
        need(time.monotonic_ns() < deadline, 'NATIVE_LAUNCH_DEADLINE_EXCEEDED')
        process = subprocess.Popen([profile['pythonPin']['path'], profile['scriptPin']['path'], '--request', args.request, '--output', args.output],
            cwd=profile['workingDirectory'], env=environment, stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=os.name == 'posix')
        start_id = process_start(process, actual_host['bootId'])
        write(root / 'native-process-binding.json', dict(schemaVersion='RecoveryControlObservationBinding/v1',
            operationId=request['operationId'], requestId=request['requestId'], requestPin=request_pin,
            attemptId=args.attempt, observerEpoch=args.epoch, clockDomain=clock, pid=process.pid,
            processStartedAt=start_id, intentPin=intent_pin, profilePin=profile_pin))
        next_sample = time.monotonic_ns()
        while process.poll() is None:
            now = time.monotonic_ns()
            if now >= next_sample:
                # Reserve the first and terminal samples; increasing intervals keep long observations bounded.
                need(len(envelope['samples']) < 99998, 'NATIVE_OBSERVATION_SAMPLE_LIMIT')
                envelope['samples'].append(sample('EXECUTOR', stdout, stderr))
                next_sample = now + max(50000000, (now - started) // 10000)
            if time.monotonic_ns() >= deadline and not envelope['timedOut']:
                envelope['timedOut'] = True; envelope['timeoutLayer'] = 'EXECUTOR'
                write(root / 'execution-evidence.json', envelope)
            time.sleep(0.05)
        exit_code = process.returncode
    envelope['processTerminal'] = True; envelope['exits']['executor'] = exit_code
    exit_pin = write(root / 'native-original-exit.json', dict(schemaVersion='RecoveryControlNativeExit/v1',
        operationId=request['operationId'], requestId=request['requestId'], requestPin=request_pin,
        attemptId=args.attempt, observerEpoch=args.epoch, clockDomain=clock, intentPin=intent_pin,
        pid=process.pid, processStartedAt=start_id, cliExitCode=exit_code, processTerminal=True,
        timedOut=envelope['timedOut'], observedMonotonicNs=time.monotonic_ns(), observedWallNs=time.time_ns()))
    envelope['originalPins'].append(exit_pin)
    observer = profile['resourceObserverPin']
    if observer is not None and time.monotonic_ns() < deadline:
        if namespace is not None:
            namespace.recheck(True)
        verify(profile_pin)
        verify(observer)
        observer_request = dict(schemaVersion='RecoveryControlResourceObservationRequest/v1', operationId=request['operationId'],
            requestId=request['requestId'], requestPin=request_pin, attemptId=args.attempt, observerEpoch=args.epoch,
            clockDomain=clock, pid=process.pid, processStartedAt=start_id, originalExitPin=exit_pin,
            sourceOrTargetRef=request['sourceOrTargetRef'], selectedPointPin=request['selectedPointPin'],
            operationResultPath=args.output, deadlineMilliseconds=max(1, (deadline-time.monotonic_ns())//1000000))
        observer_request_pin = write(root / 'resource-observer-request.json', observer_request)
        observation_path = root / 'resource-observation.json'
        with (root / 'resource-observer-stdout').open('xb') as out, (root / 'resource-observer-stderr').open('xb') as err:
            if os.name == 'posix': os.chmod(out.name, 0o600); os.chmod(err.name, 0o600)
            observer_process = subprocess.Popen([profile['pythonPin']['path'], observer['path'], '--request', observer_request_pin['path'], '--output', str(observation_path)],
                cwd=profile['workingDirectory'], env=environment, stdin=subprocess.DEVNULL, stdout=out, stderr=err)
            # Observer is read-only. Timeout never kills it or fabricates terminal success.
            try: observer_exit = observer_process.wait(timeout=max(0.001, (deadline-time.monotonic_ns())/1e9))
            except subprocess.TimeoutExpired: observer_exit = None
        if observer_exit == 0 and observation_path.is_file():
            resource_pin = pin(observation_path); resource = document(resource_pin)
            need(resource['schemaVersion'] == 'RecoveryControlResourceObservation/v1' and resource['operationId'] == request['operationId'] and
                 resource['requestId'] == request['requestId'] and resource['requestPin'] == request_pin and
                 resource['attemptId'] == args.attempt and resource['observerEpoch'] == args.epoch and resource['clockDomain'] == clock and
                 resource['pid'] == process.pid and resource['processStartedAt'] == start_id and resource['originalExitPin'] == exit_pin and
                 type(resource['resourceTerminal']) is bool and resource['originalPins'], 'RESOURCE_OBSERVATION_BINDING_INVALID')
            for reference in resource['originalPins']: verify(reference)
            envelope['resourceTerminal'] = resource['resourceTerminal']; envelope['originalPins'].append(resource_pin)
        elif observer_exit is None:
            envelope['timedOut'] = True; envelope['timeoutLayer'] = 'EXECUTOR'
    envelope['streamRefs'] = dict(stdout=pin(stdout), stderr=pin(stderr))
    envelope['originalPins'].extend(envelope['streamRefs'].values())
    if namespace is not None:
        namespace.recheck(True)
    verify(profile_pin)
    envelope['samples'].append(sample('ORIGINAL_EXIT', stdout, stderr)); envelope['complete'] = True
    write(root / 'execution-evidence.json', envelope)
    if namespace is not None:
        namespace.recheck(True)
        namespace.close()
    return 2 if envelope['timedOut'] else exit_code


def prepare_lab_context(args):
    need(args.profile is None and args.lab_dispatch is None and args.authority_inputs and args.authority_inputs_sha256
         and args.authorization and args.authorization_sha256 and args.lease and args.lease_sha256 and args.issued_at and args.expires_at,
         'LAB_PREPARATION_ARGUMENT_REQUIRED')
    selected = pin(args.authority_inputs); need(selected['sha256'] == args.authority_inputs_sha256, 'LAB_AUTHORITY_INPUTS_CHANGED')
    inputs = document(selected)
    fields(inputs, 'schemaVersion executionHostPin servicePin programPin authorityKeyPin', 'LAB_PREPARATION_FIELDS_INVALID')
    need(inputs['schemaVersion'] == 'RecoveryControlBackupLabAuthorityInputs/v1', 'LAB_PREPARATION_VERSION_INVALID')
    # The same installed helper must be independently signed before its code is executed.
    import base64
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    key_pin = selected_lab_authority(args, inputs)
    key = load_pem_public_key(pinned_read(key_pin['path'], True)[1]); need(isinstance(key, Ed25519PublicKey), 'LAB_AUTHORITY_KEY_INVALID')
    host = document(inputs['executionHostPin']); install = document(host['installationManifestPin'])
    fields(install, 'schemaVersion keySha256 payload signature', 'LAB_INSTALLATION_ENVELOPE_INVALID')
    need(install['schemaVersion'] == 'RepositorySignedRecord/v1' and install['keySha256'] == key_pin['sha256'], 'LAB_INSTALLATION_SIGNER_INVALID')
    key.verify(base64.b64decode(install['signature'], validate=True), json.dumps(install['payload'], ensure_ascii=False,
               sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8'))
    helper = Path(__file__).resolve().with_name('recovery_control_lab.py'); helper_pin = pin(helper)
    need(helper_pin in install['payload']['filePins'], 'LAB_AUTHORITY_HELPER_NOT_INSTALLED')
    raw = pinned_read(helper, True)[1]; need(pin(helper) == helper_pin, 'LAB_AUTHORITY_HELPER_CHANGED')
    import types
    module = types.ModuleType('recovery_control_lab'); module.__file__ = str(helper)
    exec(compile(raw, str(helper), 'exec'), module.__dict__)
    request_pin = pin(args.request); need(request_pin['sha256'] == args.request_sha256, 'NATIVE_REQUEST_CHANGED')
    authorization = pin(args.authorization); need(authorization['sha256'] == args.authorization_sha256, 'LAB_AUTHORIZATION_CHANGED')
    lease = pin(args.lease); need(lease['sha256'] == args.lease_sha256, 'LAB_LEASE_CHANGED')
    _, _, payload = module.admit(sys.modules[__name__], selected, request_pin, Path(__file__).resolve(),
                               dict(authorizationPin=authorization, leasePin=lease, issuedAt=args.issued_at, expiresAt=args.expires_at), authority_pin=key_pin)
    output = Path(args.output)
    need(output.is_absolute() and output.resolve() == output and str(output).startswith(module.ROOT + '/') and not output.exists(), 'LAB_PREPARATION_OUTPUT_SCOPE_INVALID')
    parent = output.parent.stat(); need(parent.st_uid == parent.st_gid == 0 and parent.st_mode & 0o777 == 0o700, 'LAB_PREPARATION_OUTPUT_PRIVATE_REQUIRED')
    # Exclusive unsigned original. No private authority key or business executor is used.
    with output.open('xb') as stream:
        os.chmod(output, 0o600); stream.write(module.canonical(payload)); stream.flush(); os.fsync(stream.fileno())
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--identity', action='store_true')
    parser.add_argument('--lab-dispatch')
    parser.add_argument('--lab-dispatch-sha256')
    parser.add_argument('--prepare-lab-context', action='store_true')
    for name in ('authority-inputs', 'authority-inputs-sha256', 'authorization', 'authorization-sha256', 'lease', 'lease-sha256', 'issued-at', 'expires-at'):
        parser.add_argument('--' + name)
    for name in ('profile', 'profile-sha256', 'request', 'request-sha256', 'output', 'attempt', 'epoch', 'verification-binding', 'verification-binding-sha256'):
        parser.add_argument('--' + name)
    parser.add_argument('--verification-binding-bytes', type=int)
    parser.add_argument('--lab-authority-key')
    parser.add_argument('--lab-authority-key-sha256')
    parser.add_argument('--lab-authority-key-bytes', type=int)
    parser.add_argument('--lab-native-launch')
    parser.add_argument('--lab-native-launch-sha256')
    parser.add_argument('--lab-native-launch-bytes', type=int)
    parser.add_argument('--verify-lab-installation', action='store_true')
    parser.add_argument('--installation')
    parser.add_argument('--installation-sha256')
    parser.add_argument('--installation-bytes', type=int)
    parser.add_argument('--read-budget-milliseconds', type=int)
    args = parser.parse_args()
    try:
        if args.identity:
            print(json.dumps(identity(), sort_keys=True)); return 0
        if args.verify_lab_installation:
            need(args.installation and args.installation_sha256 and args.installation_bytes is not None,
                 'LAB_INSTALLATION_ARGUMENT_REQUIRED')
            authority = selected_lab_authority(args)
            need(args.read_budget_milliseconds is not None and 0 < args.read_budget_milliseconds <= 60000,
                 'LAB_READ_BUDGET_REQUIRED')
            manifest = native_installation(dict(path=args.installation, sha256=args.installation_sha256, bytes=args.installation_bytes),
                                           authority, deadline=time.monotonic() + args.read_budget_milliseconds / 1000)
            print(json.dumps(manifest, sort_keys=True, separators=(',', ':'))); return 0
        if args.prepare_lab_context:
            need(args.request and args.request_sha256 and args.output, 'LAB_PREPARATION_ARGUMENT_REQUIRED')
            return prepare_lab_context(args)
        need(all(getattr(args, name) for name in ('request', 'request_sha256', 'output', 'attempt', 'epoch')) and
             ((args.lab_dispatch and args.lab_dispatch_sha256) or (args.profile and args.profile_sha256)), 'NATIVE_DISPATCH_ARGUMENT_REQUIRED')
        return run(args)
    except Exception as error:
        # Arbitrary exception text and native streams may carry credentials.
        code = str(error) if type(error) is RuntimeError and re.fullmatch('[A-Z][A-Z0-9_]{0,120}', str(error)) else type(error).__name__.upper()
        print('CONTROL_NATIVE_' + code, file=sys.stderr); return 2


if __name__ == '__main__':
    sys.exit(main())
