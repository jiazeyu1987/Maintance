"""Explicit private same-host lab admission; never a production failure path."""
from __future__ import annotations

import base64
import importlib.util
import os
from pathlib import Path
import sys

from recovery_engine import (absolute, authorities, canonical, check_pin, current_window, pinned_json,
                             require, pin)

LAB_ROOT = '/mnt/intruoyi-data/backup-restore-lab/20261012-w01-w07'
LAB_HOST = '172.30.30.59'
LAB_PREFIX = 'brlab-20261012'
REHEARSAL_ID = 'backup-server-rehearsal-20261012-r1'
PROFILE_FIELDS = set(('schemaVersion authorityKeyPin executionHostPin '
    'installedClosurePin labScopePin repositoryAuthorityKeyPins copyProtectionEvidenceKeyPins '
    'copyProtectionPinsByManifestSha256').split())
CONTEXT_FIELDS = set(('schemaVersion rehearsalId environment sourceIdentityPin executionHostPin '
    'labScopePin operationRequestPin installedClosurePin authorizationPin leasePin authorityKeyPin '
    'issuedAt expiresAt').split())
SCOPE_FIELDS = set(('schemaVersion rehearsalId repositoryId sourceIdentityPin host root '
    'resourcePrefix allowedActions expiresAt').split())
HOST_FIELDS = set(('schemaVersion hostOs hostId bootId uid gid pidNamespace mountNamespace '
    'pythonPin sourceProfilePin dispatcherPin resourceObserverPin workingDirectory evidenceRoot '
    'environment installationManifestPin').split())
COPY_FIELDS = set(('schemaVersion repositoryId sourceIdentityPin labScopePin sourceDeletionDenied '
    'independentFailureDomain recoveryKeysAvailable aclEvidencePin readbackEndpointEvidencePin validUntil').split())
SOURCE_FIELDS = set(('schemaVersion environment sourceIdentityPin materialPaths endpointHosts '
                     'captureContextPin captureSourceScopePin').split())
ACL_FIELDS = set(('schemaVersion labScopePin sourceIdentityPin archiveRoot sourceAccountPin '
                  'writerAccountPin readerAccountPin deletionAttemptPin keyAccessEvidencePin').split())
READBACK_FIELDS = set(('schemaVersion labScopePin archiveRoot uncRoot encrypted signingRequired '
                       'independentConnectionId readerAccountPin readbackOriginalPin observedAt').split())
LAB_ACTIONS = frozenset(('BACKUP_FULL BACKUP_INCREMENTAL LIST_POINTS POINT_DETAIL READBACK_VERIFY '
    'RESTORE_PREFLIGHT PREPARE_TARGET RESTORE_EXECUTE START_APPLICATION VERIFY_RECOVERY '
    'REHEARSAL PLAN_REHEARSAL').split())
GRANT_FIELDS = set(('schemaVersion operationId targetId executorId mode actions notBefore expiresAt approved').split())
LEASE_FIELDS = set(('schemaVersion operationId targetId executorId leaseId fenceToken notBefore expiresAt state').split())
OPERATION_FIELDS = set(('schemaVersion operationId requestId action mode selectedPointPin sourceOrTargetRef '
                       'policyPin authorizationRefs leaseRef inputPins deadlineMilliseconds').split())


def actions(value):
    require(type(value) is list and value and all(type(item) is str for item in value) and
            len(value) == len(set(value)) and set(value) <= LAB_ACTIONS, 'LAB_ACTIONS_INVALID')
    return set(value)


def required_actions(request):
    # RESTORE_EXECUTE remains required by W04's existing preflight/restore guards.
    required = {'RESTORE_PREFLIGHT': {'RESTORE_PREFLIGHT', 'RESTORE_EXECUTE'},
                'RESTORE_EXECUTE': {'RESTORE_EXECUTE'},
                'REHEARSAL': {'REHEARSAL', 'RESTORE_EXECUTE', 'PREPARE_TARGET', 'START_APPLICATION'}}
    require(request['mode'] == 'REHEARSAL' and request['action'] in required, 'LAB_REHEARSAL_ONLY')
    return required[request['action']]


def timestamp(value):
    from datetime import datetime
    require(type(value) is str and value.endswith('Z'), 'UTC_WINDOW_REQUIRED')
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def exact(value, fields, schema):
    require(type(value) is dict and set(value) == fields and value['schemaVersion'] == schema,
            'LAB_RECORD_INVALID_' + schema.split('/')[0].upper())
    return value


def signed(ref, keys):
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    value = pinned_json(ref)
    exact(value, {'schemaVersion', 'keySha256', 'payload', 'signature'}, 'RepositorySignedRecord/v1')
    selected = [key for key in keys if key['sha256'] == value['keySha256']]
    require(len(selected) == 1, 'LAB_AUTHORITY_UNKNOWN')
    key = load_pem_public_key(check_pin(selected[0]))
    require(isinstance(key, Ed25519PublicKey), 'LAB_AUTHORITY_KEY_INVALID')
    key.verify(base64.b64decode(value['signature'], validate=True), canonical(value['payload']))
    return value['payload']


def within_root(path):
    path = absolute(path)
    require(path == Path(LAB_ROOT) or Path(LAB_ROOT) in path.parents, 'LAB_PATH_OUT_OF_SCOPE')
    return path


def scope_record(profile, policy, required=()):
    scope = exact(signed(profile['labScopePin'], profile['repositoryAuthorityKeyPins']),
                  SCOPE_FIELDS, 'RepositoryLabScope/v1')
    require(scope['rehearsalId'] == REHEARSAL_ID and scope['repositoryId'] == policy['repositoryId'] and
            scope['host'] == LAB_HOST and scope['root'] == LAB_ROOT and scope['resourcePrefix'] == LAB_PREFIX and
            set(required) <= actions(scope['allowedActions']),
            'LAB_SCOPE_NOT_AUTHORIZED')
    current_window({'validFrom': '1970-01-01T00:00:00Z', 'validUntil': scope['expiresAt']})
    check_pin(scope['sourceIdentityPin'])
    return scope


def context_record(ref, profile, scope, *, historical=False):
    context = exact(signed(ref, [profile['authorityKeyPin']]), CONTEXT_FIELDS,
                    'BackupRehearsalAuthorityContext/v1')
    require(context['rehearsalId'] == REHEARSAL_ID and context['environment'] == 'backup-lab' and
            context['sourceIdentityPin'] == scope['sourceIdentityPin'] and
            all(context[name] == profile[name] for name in ('executionHostPin', 'labScopePin',
                                                           'installedClosurePin', 'authorityKeyPin')),
            'LAB_CONTEXT_BINDING_INVALID')
    if historical:
        # Capture provenance remains signed and immutable after its lease ends.
        from datetime import datetime, timezone
        issued = datetime.fromisoformat(context['issuedAt'].replace('Z', '+00:00'))
        expires = datetime.fromisoformat(context['expiresAt'].replace('Z', '+00:00'))
        require(context['issuedAt'].endswith('Z') and context['expiresAt'].endswith('Z') and
                issued < expires and issued <= datetime.now(timezone.utc), 'LAB_CAPTURE_CONTEXT_TIME_INVALID')
    else:
        current_window({'validFrom': context['issuedAt'], 'validUntil': context['expiresAt']})
    for name in CONTEXT_FIELDS - {'schemaVersion', 'rehearsalId', 'environment', 'issuedAt', 'expiresAt'}:
        check_pin(context[name], content=False)
    if historical:
        capture_provenance(context, profile, scope)
    return context


def capture_provenance(context, profile, scope):
    """Expired capture authority proves provenance, never current restore authority."""
    request = exact(pinned_json(context['operationRequestPin']), OPERATION_FIELDS, 'backup-restore-operation/v1')
    require(request['mode'] == 'REHEARSAL' and request['action'] in {'BACKUP_FULL', 'BACKUP_INCREMENTAL'} and
            request['action'] in actions(scope['allowedActions']) and
            context['authorizationPin'] in request['authorizationRefs'] and context['leasePin'] == request['leaseRef'],
            'LAB_CAPTURE_OPERATION_BINDING_INVALID')
    source = pinned_json(request['sourceOrTargetRef'])
    require(source['schemaVersion'] == 'RepositoryNativeBackupSource/v1' and
            source['sourceIdentityPin'] == context['sourceIdentityPin'] and
            source['executionHostPin'] == context['executionHostPin'], 'LAB_CAPTURE_SOURCE_BINDING_INVALID')
    grant = exact(signed(context['authorizationPin'], profile['repositoryAuthorityKeyPins']),
        set(('schemaVersion repositoryId operationId actions sourceOrTargetRef policyPin resourcePin '
             'notBefore expiresAt leaseRef').split()), 'RepositoryAuthorization/v1')
    lease = exact(signed(context['leasePin'], profile['repositoryAuthorityKeyPins']),
        set(('schemaVersion repositoryId operationId ownerIdentityPin expiresAt').split()), 'RepositoryLease/v1')
    require(grant['repositoryId'] == lease['repositoryId'] == scope['repositoryId'] and
            grant['operationId'] == lease['operationId'] == request['operationId'] and
            request['action'] in actions(grant['actions']) and
            grant['sourceOrTargetRef'] == grant['resourcePin'] == request['sourceOrTargetRef'] and
            grant['policyPin'] == request['policyPin'] and grant['leaseRef'] == request['leaseRef'] and
            timestamp(grant['notBefore']) <= timestamp(context['issuedAt']) < timestamp(context['expiresAt']) <=
            min(timestamp(grant['expiresAt']), timestamp(lease['expiresAt']), timestamp(scope['expiresAt'])),
            'LAB_CAPTURE_AUTHORITY_BINDING_INVALID')
    check_pin(lease['ownerIdentityPin'], content=False)


def current_authority(request, context, scope, target_identity_pin, trust):
    """Check the selected grant itself; another request/grant cannot fill its gap."""
    required = required_actions(request)
    require(required <= actions(scope['allowedActions']), 'LAB_SCOPE_NOT_AUTHORIZED')
    require(pinned_json(context['operationRequestPin']) == request and context['leasePin'] == request['leaseRef'] and
            context['authorizationPin'] in request['authorizationRefs'], 'LAB_CURRENT_OPERATION_BINDING_INVALID')
    grant = exact(pinned_json(context['authorizationPin']), GRANT_FIELDS, 'RecoveryEnvironmentAuthorization/v1')
    lease = exact(pinned_json(context['leasePin']), LEASE_FIELDS, 'RecoveryEnvironmentLease/v1')
    require(required <= actions(grant['actions']), 'LAB_CURRENT_GRANT_ACTION_REQUIRED')
    require(timestamp(context['expiresAt']) <= min(timestamp(grant['expiresAt']), timestamp(lease['expiresAt']),
                                                 timestamp(scope['expiresAt'])) and
            timestamp(context['issuedAt']) >= max(timestamp(grant['notBefore']), timestamp(lease['notBefore'])),
            'LAB_CURRENT_AUTHORITY_WINDOW_INVALID')
    authorities(request, target_identity_pin, required, trust)


def selected_context():
    path = os.environ.get('INTRUOYI_BACKUP_LAB_CONTEXT_PATH')
    sha = os.environ.get('INTRUOYI_BACKUP_LAB_CONTEXT_SHA256')
    require(path and sha, 'LAB_CURRENT_CONTEXT_SELECTION_REQUIRED')
    ref = pin(absolute(path))
    require(ref['sha256'] == sha, 'LAB_CURRENT_CONTEXT_SELECTION_CHANGED')
    return ref


def acyclic_inputs(values, context_ref):
    """No stable request dependency may refer back to this operation context."""
    from recovery_cli import PublicOutput
    seen = {}; visiting = set(); expanded = set()
    def walk(value, *, leaf=False):
        if type(value) is dict:
            if set(value) == {'path','bytes','sha256'}:
                require(value['path'] != context_ref['path'], 'LAB_CURRENT_CONTEXT_PIN_CYCLE')
                identity = (value['path'],value['sha256'])
                require(identity not in visiting, 'LAB_STABLE_INPUT_PIN_CYCLE')
                previous = seen.get(value['path'])
                if previous is not None:
                    require(previous == value, 'LAB_STABLE_INPUT_PIN_CONFLICT')
                else:
                    require(len(seen) < 4096, 'LAB_STABLE_INPUT_PIN_GRAPH_TOO_LARGE')
                    seen[value['path']] = value
                if leaf: return  # Byte originals count, but cannot expand configuration edges.
                if identity in expanded: return
                visiting.add(identity);walk(pinned_json(value));visiting.remove(identity);expanded.add(identity)
            else:
                byte_containers = PublicOutput.BYTE_CONTAINERS_BY_SCHEMA.get(value.get('schemaVersion'), set())
                for name,node in value.items():
                    walk(node,leaf=leaf or name in PublicOutput.BYTE_INPUTS or name in byte_containers)
        elif type(value) is list:
            for node in value: walk(node,leaf=leaf)
    for value in values: walk(value)


def host_contract(host, profile):
    exact(host, HOST_FIELDS, 'RepositoryNativeExecutionHost/v1')
    require(host['hostOs'] == 'Linux' and type(host['uid']) is int and type(host['gid']) is int and
            host['uid'] == host['gid'] == 0 and
            host['installationManifestPin'] == profile['installedClosurePin'], 'LAB_NATIVE_HOST_REQUIRED')
    environment = host['environment']
    require(type(environment) is dict and all(type(name) is str and name and '\0' not in name and '=' not in name and
            type(value) is str and '\0' not in value and name not in {'PYTHONPATH', 'PYTHONHOME'} and
            not name.startswith(('INTRUOYI_BACKUP_LAB_', 'INTRUOYI_REPOSITORY_LAB_', 'INTRUOYI_REPOSITORY_HOST_VIEW_'))
            for name, value in environment.items()), 'LAB_STATIC_HOST_ENVIRONMENT_REQUIRED')
    return host


def native_installation(reference, authority_pins):
    """Select v2 explicitly; only W03's pinned helper admits native origins."""
    installed = signed(reference, authority_pins)
    require(type(installed) is dict, 'LAB_INSTALLATION_RECORD_INVALID')
    version = installed.get('schemaVersion')
    fields = set(('schemaVersion root sourceToolkitPin filePins pythonPin dependencyPins').split())
    require(version in {'RepositoryNativeInstallation/v1', 'RepositoryNativeInstallation/v2'},
            'LAB_INSTALLATION_VERSION_INVALID')
    if version == 'RepositoryNativeInstallation/v2':
        fields |= {'nativeRuntimeTrustPin', 'nativeRuntimeProofPin'}
    exact(installed, fields, version)
    require(installed['root'] == LAB_ROOT and type(installed['filePins']) is list and installed['filePins'] and
            type(installed['dependencyPins']) is list and installed['dependencyPins'], 'LAB_INSTALLED_CLOSURE_REQUIRED')
    closure = installed['filePins'] + installed['dependencyPins'] + [installed['pythonPin']]
    require(len(closure) <= 4096, 'LAB_INSTALLATION_GRAPH_TOO_LARGE')
    require(len({ref['path'] for ref in closure}) == len(closure), 'LAB_INSTALLATION_DUPLICATE_PATH')
    if version == 'RepositoryNativeInstallation/v1':
        for ref in closure:
            within_root(ref['path']); check_pin(ref, content=False)
            info = absolute(ref['path']).stat()
            require(info.st_uid == 0 and info.st_mode & 0o022 == 0, 'LAB_HOST_FILE_WRITABLE')
        check_pin(installed['sourceToolkitPin'], content=False)
        return installed
    # V2 does not move programs or control originals into a native exception.
    within_root(reference['path'])
    for name in ('sourceToolkitPin', 'nativeRuntimeTrustPin', 'nativeRuntimeProofPin'):
        within_root(installed[name]['path']); check_pin(installed[name], content=False)
    for ref in installed['filePins']:
        within_root(ref['path']); check_pin(ref, content=False)
        info = absolute(ref['path']).stat()
        require(info.st_uid == info.st_gid == 0 and info.st_mode & 0o022 == 0, 'LAB_HOST_FILE_WRITABLE')
    helpers = [ref for ref in installed['filePins'] if Path(ref['path']).name == 'repository_native_runtime.py']
    require(len(helpers) == 1, 'LAB_NATIVE_RUNTIME_HELPER_NOT_INSTALLED')
    helper_pin = helpers[0]
    helper_path = within_root(helper_pin['path'])
    records = [ref for ref in installed['filePins'] if Path(ref['path']) == helper_path.with_name('repository_records.py')]
    require(len(records) == 1, 'LAB_NATIVE_RUNTIME_RECORDS_NOT_INSTALLED')
    records_pin = records[0]
    records_raw = check_pin(records_pin)
    raw = check_pin(helper_pin)
    # Execute only the signed installation's exact original, never ambient
    # sys.path/PYTHONPATH or a second unpinned source read. No helper fork/cache.
    name = '_w04_native_runtime_' + helper_pin['sha256']
    spec = importlib.util.spec_from_file_location(name, str(helper_path))
    require(spec is not None and spec.loader is not None and name not in sys.modules,
            'LAB_NATIVE_RUNTIME_HELPER_ORIGIN_INVALID')
    module = importlib.util.module_from_spec(spec)
    records_spec = importlib.util.spec_from_file_location('repository_records', records_pin['path'])
    require(records_spec is not None and records_spec.loader is not None, 'LAB_NATIVE_RUNTIME_HELPER_ORIGIN_INVALID')
    records_module = importlib.util.module_from_spec(records_spec)
    previous_records = sys.modules.get('repository_records')
    sys.modules['repository_records'] = records_module
    sys.modules[name] = module
    try:
        # W03's shared helper imports this W03 dependency. Select its signed
        # adjacent original too, so an ambient/cached module cannot supply it.
        exec(compile(records_raw, records_pin['path'], 'exec'), records_module.__dict__)
        exec(compile(raw, str(helper_path), 'exec'), module.__dict__)
        require(callable(getattr(module, 'verify_native_installation', None)), 'LAB_NATIVE_RUNTIME_API_REQUIRED')
        verified = module.verify_native_installation(reference, authority_pins)
        require(verified == installed, 'LAB_NATIVE_RUNTIME_MANIFEST_CHANGED')
        check_pin(helper_pin, content=False)
        check_pin(records_pin, content=False)
        check_pin(reference, content=False)
    finally:
        del sys.modules[name]
        if previous_records is None:
            del sys.modules['repository_records']
        else:
            sys.modules['repository_records'] = previous_records
    return verified


def host_record(profile, policy=None):
    host = exact(pinned_json(profile['executionHostPin']), HOST_FIELDS, 'RepositoryNativeExecutionHost/v1')
    require(sys.platform == 'linux' and sys.version_info >= (3, 12) and hasattr(os, 'setns') and
            os.getuid() == os.getgid() == 0, 'LAB_NATIVE_HOST_REQUIRED')
    host_contract(host, profile)
    require(host['hostId'] == Path('/etc/machine-id').read_text().strip() and
            host['bootId'] == Path('/proc/sys/kernel/random/boot_id').read_text().strip() and
            host['pidNamespace'] == os.readlink('/proc/self/ns/pid') and
            host['mountNamespace'] == os.readlink('/proc/self/ns/mnt') and
            absolute(host['pythonPin']['path']) == Path(sys.executable).absolute(), 'LAB_NATIVE_HOST_CHANGED')
    for name in ('workingDirectory', 'evidenceRoot'):
        path = within_root(host[name]); info = path.stat()
        require(path.is_dir() and info.st_uid == info.st_gid == 0 and info.st_mode & 0o777 == 0o700,
                'LAB_PRIVATE_HOST_DIRECTORY_REQUIRED')
    require(Path.cwd() == Path(host['workingDirectory']), 'LAB_WORKING_DIRECTORY_CHANGED')
    selected_installation = signed(host['installationManifestPin'], profile['repositoryAuthorityKeyPins'])
    require(type(selected_installation) is dict and selected_installation.get('schemaVersion') in
            {'RepositoryNativeInstallation/v1', 'RepositoryNativeInstallation/v2'}, 'LAB_INSTALLATION_VERSION_INVALID')
    legacy = selected_installation['schemaVersion'] == 'RepositoryNativeInstallation/v1'
    for name in (('pythonPin',) if legacy else ()) + ('sourceProfilePin', 'dispatcherPin', 'resourceObserverPin', 'installationManifestPin'):
        if not legacy: within_root(host[name]['path'])
        check_pin(host[name], content=False)
        info = absolute(host[name]['path']).stat()
        require(info.st_uid == 0 and info.st_mode & 0o022 == 0, 'LAB_HOST_FILE_WRITABLE')
    registration = pinned_json(host['sourceProfilePin'])
    require(registration['schemaVersion'] == 'RecoveryLocalEnvironmentRegistration/v1' and
            registration['usableForExecution'] is True and registration['host']['selectedExecutionHost'] is not None,
            'LAB_HOST_REGISTRATION_REQUIRED')
    installed = native_installation(host['installationManifestPin'], profile['repositoryAuthorityKeyPins'])
    require(installed['root'] == LAB_ROOT and installed['pythonPin'] == host['pythonPin'] and
            type(installed['filePins']) is list and installed['filePins'] and
            type(installed['dependencyPins']) is list and installed['dependencyPins'] and
            host['dispatcherPin'] in installed['filePins'] and host['resourceObserverPin'] in installed['filePins'],
            'LAB_INSTALLED_CLOSURE_REQUIRED')
    if policy is not None:
        for ref in policy['moduleSourcePins'] + [policy['dataWorkerPin']]:
            within_root(ref['path']); check_pin(ref, content=False)
        require(all(ref in installed['filePins'] for ref in policy['moduleSourcePins']) and
                policy['dataWorkerPin'] in installed['filePins'], 'LAB_W04_CLOSURE_NOT_INSTALLED')
    return host


def source_record(ref, profile, scope):
    """W04's consumer scope is distinct from W02's exact capture/ledger scope."""
    source = exact(pinned_json(ref), SOURCE_FIELDS, 'RecoveryDataLabSourceScope/v1')
    require(source['environment'] == 'backup-lab' and source['sourceIdentityPin'] == scope['sourceIdentityPin'] and
            type(source['materialPaths']) is list and source['materialPaths'] and
            type(source['endpointHosts']) is list and source['endpointHosts'] and
            all(type(host) is str and '\0' not in host and
                (host in {LAB_HOST, '127.0.0.1', 'localhost'} or host.startswith(LAB_PREFIX+'-'))
                for host in source['endpointHosts']),
            'LAB_SOURCE_SCOPE_INVALID')
    context = context_record(source['captureContextPin'], profile, scope, historical=True)
    capture = pinned_json(source['captureSourceScopePin'])
    identity = pinned_json(source['sourceIdentityPin'])
    capture_scope_binding(source, context, capture, identity)
    for path in source['materialPaths']: within_root(path)
    return source


def capture_scope_binding(source, context, capture, identity):
    """The retained scope comes from this capture request's stable W03 template."""
    exact(capture, {'schemaVersion', 'environment', 'targetRawSha256', 'targetFingerprint',
                    'database', 'databaseUuid', 'labContextPin'}, 'backup-lab-source-scope/v1')
    require(capture['environment'] == 'backup-lab' and capture['labContextPin'] == source['captureContextPin'] and
            capture['targetFingerprint'] == identity['sourceFingerprint'] and
            capture['databaseUuid'] == identity['databaseUuid'], 'LAB_CAPTURE_SOURCE_BINDING_INVALID')
    request = pinned_json(context['operationRequestPin'])
    capture_source = pinned_json(request['sourceOrTargetRef'])
    template = pinned_json(capture_source['captureRequestPin'])
    require(template['schemaVersion'] == 'backup-lab-capture-request-template/v1' and
            'labContextPin' not in template, 'LAB_STABLE_CAPTURE_TEMPLATE_REQUIRED')
    template_scope = exact(template['sourceScope'], {'schemaVersion', 'environment', 'targetRawSha256',
        'targetFingerprint', 'database', 'databaseUuid'}, 'backup-lab-source-scope-template/v1')
    require(capture == dict(template_scope, schemaVersion='backup-lab-source-scope/v1',
                            labContextPin=source['captureContextPin']), 'LAB_CAPTURE_TEMPLATE_BINDING_INVALID')


def admit(request, policy, trust, target):
    """Called again by existing guards before each effect, with original request."""
    required = required_actions(request)
    require(policy['schemaVersion'] == 'RecoveryDataLabPolicy/v1' and
            trust['schemaVersion'] == 'RecoveryDataLabTrust/v1' and
            trust['labProfilePin'] == policy['labProfilePin'], 'LAB_PROFILE_NOT_INDEPENDENTLY_TRUSTED')
    profile = exact(pinned_json(policy['labProfilePin']), PROFILE_FIELDS, 'RecoveryDataLabProfile/v2')
    require(type(profile['repositoryAuthorityKeyPins']) is list and profile['repositoryAuthorityKeyPins'] and
            type(profile['copyProtectionEvidenceKeyPins']) is list and profile['copyProtectionEvidenceKeyPins'] and
            type(profile['copyProtectionPinsByManifestSha256']) is dict, 'LAB_PROVISIONED_EVIDENCE_REQUIRED')
    scope = scope_record(profile, policy, required)
    context_ref = selected_context()
    acyclic_inputs([request, policy, trust, target], context_ref)
    context = context_record(context_ref, profile, scope)
    current_authority(request, context, scope, pinned_json(policy['dataTargetPin'])['targetIdentityPin'], trust)
    host = host_record(profile, policy)
    require(host['pythonPin'] == policy['pythonPin'] == target['pythonPin'], 'LAB_PYTHON_MISMATCH')
    source = source_record(policy['sourceScopePin'], profile, scope)
    data_target = pinned_json(policy['dataTargetPin'])
    within_root(data_target['versionedDataLocation']); within_root(data_target['existingDataLocation'])
    within_root(policy['evidenceRoot'])
    require(data_target['restoreMode'] == 'REBUILD_EMPTY', 'LAB_FRESH_TARGET_REQUIRED')
    catalog = {ref['sha256']: ref for ref in policy['repositoryPointPins']}
    seen = set()
    def consume(ref):
        require(catalog.get(ref['sha256']) == ref, 'LAB_POINT_NOT_IN_CATALOG')
        require(ref['sha256'] not in seen, 'LAB_CHAIN_CYCLE_OR_DUPLICATE')
        seen.add(ref['sha256'])
        require(len(seen) <= policy['maxChainLength'], 'CHAIN_LENGTH_LIMIT')
        point = pinned_json(ref)
        chain_binding(point, pinned_json(point['manifestPin']), source, policy)
        # ParentPointPins is the full prefix, so consume each original once.
        for parent in point['parentPointPins']:
            if parent['sha256'] not in seen: consume(parent)
    require(request['selectedPointPin'] is not None, 'SELECTED_POINT_REQUIRED')
    consume(request['selectedPointPin'])
    return context_ref


def copy_protection(manifest, policy, *, archive_root=None):
    profile = exact(pinned_json(policy['labProfilePin']), PROFILE_FIELDS, 'RecoveryDataLabProfile/v2')
    scope = scope_record(profile, policy)
    selected = profile['copyProtectionPinsByManifestSha256']
    # Selection by original manifest hash is performed by the caller.
    require(manifest['copyProtectionPin'] in selected.values(), 'LAB_COPY_PROTECTION_NOT_PROVISIONED')
    proof = exact(signed(manifest['copyProtectionPin'], profile['repositoryAuthorityKeyPins']),
                  COPY_FIELDS, 'RepositoryLabCopyProtection/v1')
    require(proof['repositoryId'] == policy['repositoryId'] and
            proof['sourceIdentityPin'] == manifest['sourceIdentityPin'] == scope['sourceIdentityPin'] and
            proof['labScopePin'] == profile['labScopePin'] and proof['independentFailureDomain'] is False and
            proof['sourceDeletionDenied'] is True and proof['recoveryKeysAvailable'] is True,
            'LAB_COPY_PROTECTION_UNPROVEN')
    current_window({'validFrom': '1970-01-01T00:00:00Z', 'validUntil': proof['validUntil']})
    keys = profile['copyProtectionEvidenceKeyPins']
    acl = exact(signed(proof['aclEvidencePin'], keys), ACL_FIELDS, 'RepositoryLabAclEvidence/v1')
    endpoint = exact(signed(proof['readbackEndpointEvidencePin'], keys), READBACK_FIELDS,
                     'RepositoryLabReadbackEndpoint/v1')
    require(acl['labScopePin'] == endpoint['labScopePin'] == proof['labScopePin'] and
            acl['sourceIdentityPin'] == proof['sourceIdentityPin'] and
            type(acl['archiveRoot']) is str and acl['archiveRoot'] == endpoint['archiveRoot'] and
            acl['readerAccountPin'] == endpoint['readerAccountPin'] and
            endpoint['encrypted'] is True and endpoint['signingRequired'] is True and
            type(endpoint['independentConnectionId']) is str and endpoint['independentConnectionId'] and
            '\0' not in endpoint['independentConnectionId'], 'LAB_EVIDENCE_BINDING_INVALID')
    from pathlib import PurePosixPath
    root = PurePosixPath(acl['archiveRoot'])
    require(root.is_absolute() and str(root) == acl['archiveRoot'] and '..' not in root.parts and
            root.name == 'archives' and PurePosixPath(LAB_ROOT) in root.parents and
            (archive_root is None or str(archive_root) == acl['archiveRoot']), 'LAB_ARCHIVE_ROOT_MISMATCH')
    unc = endpoint['uncRoot']
    require(type(unc) is str and unc.startswith('\\\\'+LAB_HOST+'\\') and
            len(unc.split('\\')) == 4 and unc.split('\\')[3].startswith(LAB_PREFIX) and '\0' not in unc,
            'LAB_READBACK_ENDPOINT_OUT_OF_SCOPE')
    accounts = [acl[name] for name in ('sourceAccountPin', 'writerAccountPin', 'readerAccountPin')]
    for ref in accounts: check_pin(ref, content=False)
    require(len({ref['sha256'] for ref in accounts}) == 3, 'LAB_INDEPENDENT_READER_REQUIRED')
    deletion = exact(signed(acl['deletionAttemptPin'], keys),
        set(('schemaVersion labScopePin accountPin archiveRoot deleteDenied probeOriginalPin').split()),
        'RepositoryLabDeletionProbe/v1')
    key_access = exact(signed(acl['keyAccessEvidencePin'], keys),
        set(('schemaVersion labScopePin recoveryKeysAvailable probeOriginalPin').split()), 'RepositoryLabKeyAccess/v1')
    require(deletion['labScopePin'] == key_access['labScopePin'] == proof['labScopePin'] and
            deletion['accountPin'] == acl['sourceAccountPin'] and deletion['archiveRoot'] == acl['archiveRoot'] and
            deletion['deleteDenied'] is True and key_access['recoveryKeysAvailable'] is True,
            'LAB_DELETION_OR_KEY_ACCESS_UNPROVEN')
    originals = [deletion['probeOriginalPin'], key_access['probeOriginalPin'], endpoint['readbackOriginalPin']]
    for ref in originals: check_pin(ref, content=False)
    from datetime import datetime, timezone
    observed = timestamp(endpoint['observedAt'])
    age = (datetime.now(timezone.utc) - observed).total_seconds()
    require(0 <= age <= policy['maximumProofAgeSeconds'] and observed < timestamp(proof['validUntil']),
            'LAB_COPY_PROTECTION_EVIDENCE_STALE')
    return [manifest['copyProtectionPin'], proof['aclEvidencePin'], proof['readbackEndpointEvidencePin'],
            acl['deletionAttemptPin'], acl['keyAccessEvidencePin'], *accounts, *originals]


def chain_binding(candidate, manifest, source_scope, policy):
    if policy['schemaVersion'] != 'RecoveryDataLabPolicy/v1':
        require(source_scope.get('environment') != 'backup-lab' and
                source_scope.get('schemaVersion') not in ('backup-lab-source-scope/v1', 'RecoveryDataLabSourceScope/v1'),
                'LAB_MATERIAL_IN_PRODUCTION_POLICY')
        # A lab proof cannot be consumed through the production selector.
        proof = pinned_json(manifest['copyProtectionPin'])
        require(proof.get('schemaVersion') != 'RepositoryLabCopyProtection/v1' and
                (type(proof.get('payload')) is not dict or
                 proof['payload'].get('schemaVersion') != 'RepositoryLabCopyProtection/v1'),
                'LAB_COPY_PROTECTION_IN_PRODUCTION_POLICY')
        return []
    profile = pinned_json(policy['labProfilePin'])
    require(profile['copyProtectionPinsByManifestSha256'].get(candidate['manifestPin']['sha256']) ==
            manifest['copyProtectionPin'], 'LAB_MANIFEST_COPY_PROTECTION_MISMATCH')
    scope = scope_record(profile, policy)
    require(source_scope == source_record(policy['sourceScopePin'], profile, scope) and
            source_scope['sourceIdentityPin'] == manifest['sourceIdentityPin'], 'LAB_CHAIN_SOURCE_MISMATCH')
    manifest_path = within_root(candidate['manifestPin']['path'])
    require(manifest_path.name == 'manifest.json' and manifest_path.parent.name == '.repository' and
            manifest_path.parents[2].name == 'archives',
            'LAB_MANIFEST_ARCHIVE_LAYOUT_INVALID')
    return copy_protection(manifest, policy, archive_root=manifest_path.parents[2])


def immutable_binding(policy, chain):
    if policy['schemaVersion'] != 'RecoveryDataLabPolicy/v1': return {}
    profile = pinned_json(policy['labProfilePin'])
    pins = []
    for _, point, material, _ in chain:
        pins.extend(chain_binding(point, pinned_json(point['manifestPin']),
                                  pinned_json(material['sourceScopePin']), policy))
    # Current authority is revalidated by admit/guards; it is not plan identity.
    return dict(labProfilePin=policy['labProfilePin'],
                executionHostPin=profile['executionHostPin'], installedClosurePin=profile['installedClosurePin'],
                labScopePin=profile['labScopePin'], copyProtectionEvidencePins=pins,
                independentFailureDomain=False, productionNasAccepted=False)
