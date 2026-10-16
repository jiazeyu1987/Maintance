"""Explicit native lab installation/authority checks; never a production fallback."""
from datetime import datetime, timezone
import os
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import sys
import time

from repository_records import (Deadline, document, exact, read_pin, require, safe_path,
                                signed_pin, timestamp)

LAB_ROOT = '/mnt/intruoyi-data/backup-restore-lab/20261012-w01-w07'
LAB_ID = 'backup-server-rehearsal-20261012-r1'
LAB_ACTIONS = frozenset({'BACKUP_FULL', 'BACKUP_INCREMENTAL', 'LIST_POINTS', 'POINT_DETAIL',
    'READBACK_VERIFY', 'RESTORE_PREFLIGHT', 'PREPARE_TARGET', 'RESTORE_EXECUTE',
    'START_APPLICATION', 'VERIFY_RECOVERY', 'REHEARSAL', 'PLAN_REHEARSAL'})
SERVICE_FIELDS = 'schemaVersion repositoryId repositoryRoot evidenceRoot schemaPin policyPin authorityKeyPins evidenceKeyPins publisherCommand implementationPins captureBinderDependencyPins recoveryApprovalPins executionHostPin labScopePin'
SOURCE_FIELDS = 'schemaVersion repositoryId sourceIdentityPin pythonPin ownerCommand nativeVerifierCommand nativeAuthorityKeyPins nativePeerConfigPin bootstrapBinding baseSchemaPin controlAddendumPin workspacePin workspaceDirectory localStagingRoot localRootIdentityPin archiveRoot archiveCredentialPin evidenceSigningKeyPin prepareRequestPin captureRequestPin executionHostPin resourceObserverPin'
HOST_FIELDS = 'schemaVersion hostOs hostId bootId uid gid pidNamespace mountNamespace pythonPin sourceProfilePin dispatcherPin resourceObserverPin workingDirectory evidenceRoot environment installationManifestPin'
ROLES = {'records': 'repository_records.py', 'catalog': 'repository_catalog.py',
         'retention': 'repository_retention.py', 'cli': 'repository_cli.py',
         'nativeBridge': 'repository_native_bridge.py', 'installerProgram': 'repository_installer.py',
         'publishProgram': 'repository_publish.py', 'binding': 'repository_binding.py',
         'nativePeer': 'repository_native_peer.py', 'nativeReadback': 'repository_native_readback.py',
         'nativePublisher': 'repository_native_publisher.py'}


def stable_graph(roots, forbidden, *, native_installation=None, deadline=None):
    """Re-read the actual transitive Pin graph before runtime derivation.

    Original request/source/policy templates cannot reference this operation's
    context, including through signed payloads or nested installation records.
    """
    forbidden_paths = {pin['path'] for pin in forbidden}
    native_members = {}
    vendor_members = {}
    if native_installation is not None:
        require(native_installation.get('schemaVersion') == 'RepositoryNativeInstallation/v2',
                'REPOSITORY_NATIVE_INSTALLATION_SCOPE_INVALID')
        trust = document(read_pin(native_installation['nativeRuntimeTrustPin']))['payload']
        native_members = {entry['pin']['path']: entry for entry in trust['nativeFilePins']}
        vendor_members = {pin['path']: pin for pin in trust['vendorArtifactPins']}
        deadline = min(time.monotonic() + 60, deadline) if deadline is not None else time.monotonic() + 60
    seen, active = {}, set()
    def walk(value):
        if native_installation is not None:
            require(time.monotonic() < deadline, 'REPOSITORY_NATIVE_READ_DEADLINE_EXPIRED')
        if type(value) is dict:
            if set(value) == {'path', 'bytes', 'sha256'} and type(value['path']) is str:
                path = value['path']
                require(path not in forbidden_paths, 'REPOSITORY_LAB_PIN_GRAPH_FEEDBACK')
                require(path not in active, 'REPOSITORY_LAB_PIN_GRAPH_CYCLE')
                if path in seen:
                    require(seen[path] == value, 'REPOSITORY_LAB_PIN_GRAPH_DRIFT')
                    return
                require(len(seen) < 4096, 'REPOSITORY_LAB_PIN_GRAPH_TOO_LARGE')
                seen[path] = value
                active.add(path)
                if path in native_members:
                    from repository_native_runtime import verify_native_file
                    from repository_native_browser_resources import BROWSER_RESOURCE_ROLE
                    verify_native_file(value, native_installation['nativeRuntimeTrustPin'],
                        native_installation['nativeRuntimeProofPin'], role=native_members[path]['roles'][0], deadline=deadline)
                    raw = b''
                    if native_members[path]['roles'] == [BROWSER_RESOURCE_ROLE]:
                        walk(native_members[path]['vendorArtifactPins'])
                elif native_installation is not None and (path in vendor_members or value['bytes'] > 128*1024*1024):
                    from repository_native_runtime import verify_native_file
                    from repository_native_browser_resources import BROWSER_RESOURCE_ORIGINALS
                    verify_native_file(value, native_installation['nativeRuntimeTrustPin'],
                        native_installation['nativeRuntimeProofPin'],
                        role='vendor-artifact' if path in vendor_members else 'installed-binary', deadline=deadline)
                    raw = read_pin(value, 128*1024*1024) if (value['bytes'] <= 128*1024*1024 and
                        value not in BROWSER_RESOURCE_ORIGINALS.values()) else b''
                else:
                    if native_installation is not None:
                        contained(path)
                    raw = read_pin(value, 128*1024*1024)
                if raw.lstrip().startswith((b'{', b'[')):
                    walk(document(raw))
                active.remove(path)
            else:
                for child in value.values(): walk(child)
        elif type(value) is list:
            for child in value: walk(child)
    walk(roots)
    return list(seen.values())


def contained(path):
    path = safe_path(path)
    root = Path(LAB_ROOT)
    require(path == root or root in path.parents, 'REPOSITORY_LAB_PATH_OUTSIDE_SCOPE')
    return path


def private(path, directory=False):
    path = contained(path)
    info = path.stat()
    require(info.st_uid == info.st_gid == 0 and
            stat.S_IMODE(info.st_mode) == (0o700 if directory else 0o600) and
            (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)),
            'REPOSITORY_LAB_PRIVATE_ORIGINAL_REQUIRED')
    return path


def installation(reference, authority_pins):
    manifest = signed_pin(reference, authority_pins)
    require(type(manifest) is dict, 'REPOSITORY_CONFIG_SCHEMA_INVALID')
    if manifest.get('schemaVersion') == 'RepositoryNativeInstallation/v2':
        from repository_native_runtime import verify_native_installation
        manifest = verify_native_installation(reference, authority_pins)
        selected = {pin['path']: pin for pin in
                    manifest['filePins'] + manifest['dependencyPins'] + [manifest['pythonPin']]}
        for path in Path(__file__).absolute().parent.glob('repository*.py'):
            require(selected.get(str(path)) is not None,
                    'REPOSITORY_NATIVE_INSTALLATION_MODULE_NOT_APPROVED')
            private(path)
        return manifest
    exact(manifest, 'schemaVersion root sourceToolkitPin filePins pythonPin dependencyPins',
          'RepositoryNativeInstallation/v1')
    require(manifest['root'] == LAB_ROOT and type(manifest['filePins']) is list and
            manifest['filePins'] and type(manifest['dependencyPins']) is list and
            manifest['dependencyPins'], 'REPOSITORY_NATIVE_INSTALLATION_CLOSURE_REQUIRED')
    selected = {}
    for pin in manifest['filePins'] + manifest['dependencyPins'] + [manifest['pythonPin']]:
        require(pin['path'] not in selected, 'REPOSITORY_NATIVE_INSTALLATION_DUPLICATE')
        selected[pin['path']] = pin
        contained(pin['path'])
        read_pin(pin, 128 * 1024 * 1024)
    read_pin(manifest['sourceToolkitPin'], 128 * 1024 * 1024)
    # Every adjacent module may be imported. The signed installation manifest
    # covers helpers as well as the fixed public implementation roles.
    for path in Path(__file__).absolute().parent.glob('repository*.py'):
        require(str(path) in selected, 'REPOSITORY_NATIVE_INSTALLATION_MODULE_NOT_APPROVED')
        private(path)
    return manifest


def execution_host(reference, authority_pins):
    host = document(read_pin(reference))
    exact(host, HOST_FIELDS, 'RepositoryNativeExecutionHost/v1')
    require(sys.platform.startswith('linux') and os.geteuid() == os.getegid() == 0 and
            sys.version_info >= (3, 12) and hasattr(os, 'setns'),
            'REPOSITORY_NATIVE_LINUX_RUNTIME_REQUIRED')
    require(host['hostOs'] == 'Linux' and host['uid'] == host['gid'] == 0 and
            host['hostId'] == Path('/etc/machine-id').read_text(encoding='ascii').strip() and
            host['bootId'] == Path('/proc/sys/kernel/random/boot_id').read_text(encoding='ascii').strip() and
            host['pidNamespace'] == os.readlink('/proc/self/ns/pid') and
            host['mountNamespace'] == os.readlink('/proc/self/ns/mnt') and
            safe_path(host['pythonPin']['path']) == Path(sys.executable).absolute(),
            'REPOSITORY_NATIVE_ACTUAL_HOST_MISMATCH')
    private(reference['path'])
    for name in ('workingDirectory', 'evidenceRoot'):
        private(host[name], directory=True)
    for name in ('pythonPin', 'sourceProfilePin', 'dispatcherPin', 'resourceObserverPin'):
        read_pin(host[name], 128 * 1024 * 1024)
    require(type(host['environment']) is dict and all(type(k) is str and type(v) is str and
            '\x00' not in k + v and '=' not in k and not k.startswith('INTRUOYI_REPOSITORY_HOST_VIEW_')
            for k, v in host['environment'].items()), 'REPOSITORY_NATIVE_ENVIRONMENT_INVALID')
    require(not host['environment'].get('PYTHONPATH') and not host['environment'].get('PYTHONHOME'),
            'REPOSITORY_NATIVE_IMPORT_OVERRIDE_REFUSED')
    require(not any(k.startswith(('INTRUOYI_BACKUP_LAB_','INTRUOYI_REPOSITORY_LAB_'))
        for k in host['environment']), 'REPOSITORY_LAB_DYNAMIC_SELECTION_IN_HOST_REFUSED')
    registration = document(read_pin(host['sourceProfilePin']))
    require(registration['schemaVersion'] == 'RecoveryLocalEnvironmentRegistration/v1' and
            registration['usableForExecution'] is True and
            registration['host']['selectedExecutionHost'] is not None,
            'REPOSITORY_NATIVE_ENVIRONMENT_NOT_USABLE')
    manifest = installation(host['installationManifestPin'], authority_pins)
    if manifest['schemaVersion'] == 'RepositoryNativeInstallation/v2':
        trust = signed_pin(manifest['nativeRuntimeTrustPin'], authority_pins)
        require(trust['runtimeRole'] == 'EXECUTOR', 'REPOSITORY_NATIVE_EXECUTOR_ROLE_REQUIRED')
    require(manifest['pythonPin'] == host['pythonPin'] and all(host[k] in manifest['filePins']
            for k in ('dispatcherPin', 'resourceObserverPin')), 'REPOSITORY_NATIVE_HOST_NOT_INSTALLED')
    return host


def lab_scope(config, request=None):
    scope = signed_pin(config.value['labScopePin'], config.value['authorityKeyPins'])
    exact(scope, 'schemaVersion rehearsalId repositoryId sourceIdentityPin host root resourcePrefix allowedActions expiresAt',
          'RepositoryLabScope/v1')
    require(scope['rehearsalId'] == LAB_ID and scope['host'] == '172.30.30.59' and
            scope['root'] == LAB_ROOT and scope['resourcePrefix'] == 'brlab-20261012' and
            scope['repositoryId'] == config.value['repositoryId'] and
            scope['sourceIdentityPin'] == config.policy['sourceIdentityPin'] and
            type(scope['allowedActions']) is list and scope['allowedActions'] and
            all(type(action) is str for action in scope['allowedActions']) and
            len(set(scope['allowedActions'])) == len(scope['allowedActions']) and
            set(scope['allowedActions']) <= LAB_ACTIONS and
            timestamp(scope['expiresAt']) > datetime.now(timezone.utc), 'REPOSITORY_LAB_SCOPE_INVALID')
    if request is not None:
        require(request['mode'] == 'REHEARSAL' and request['action'] in scope['allowedActions'],
                'REPOSITORY_LAB_ACTION_NOT_RELEASED')
    read_pin(scope['sourceIdentityPin'])
    return scope


def command(value, python_pin, arguments):
    exact(value, 'schemaVersion executablePin programPins arguments workingDirectory', 'RepositoryNativeCommand/v1')
    require(value['executablePin'] == python_pin and value['arguments'] == arguments and
            type(value['programPins']) is list and value['programPins'],
            'REPOSITORY_NATIVE_COMMAND_NOT_APPROVED')
    read_pin(python_pin, 128 * 1024 * 1024)
    private(value['workingDirectory'], directory=True)
    for pin in value['programPins']:
        private(pin['path']); read_pin(pin)


def readback_selection(reader, source, endpoint):
    """Bind the archive-only SMB export to its selected logical archive root."""
    exact(reader, 'schemaVersion uncRoot repositoryRelativePath repositoryRoot credentialPin port authProtocol recordRoot maximumRecordBytes maximumTotalRecordBytes libraryPins',
          'RepositorySmbReadbackConfig/v1')
    require(reader['uncRoot'] == endpoint['uncRoot'] and
            endpoint['archiveRoot'] == source['archiveRoot'], 'REPOSITORY_LAB_SMB_ENDPOINT_CHANGED')
    require(reader['credentialPin'] == source['archiveCredentialPin'] and
            reader['repositoryRoot'] == source['archiveRoot'] and
            source['archiveRoot'] == str(PurePosixPath(source['workspaceDirectory']) / 'archives'),
            'REPOSITORY_NATIVE_READER_NOT_SELECTED')
    return reader


def native_source_configuration(fields, *, service_pin, peer_pin):
    """Bind measured originals to a current service and authenticated peer.

    This returns an unsigned source configuration; the native producer retains
    it with write_private. It neither measures source identity nor issues trust.
    """
    derived = set('repositoryId sourceIdentityPin pythonPin ownerCommand nativeVerifierCommand nativePeerConfigPin executionHostPin resourceObserverPin'.split())
    exact(fields, ' '.join(sorted(set(SOURCE_FIELDS.split()) - derived)), 'RepositoryNativeBackupSource/v1')
    from repository_records import Configuration
    config = Configuration(service_pin)
    require(config.native_lab, 'REPOSITORY_NATIVE_SERVICE_REQUIRED')
    host = execution_host(config.value['executionHostPin'], config.value['authorityKeyPins'])
    installed = installation(host['installationManifestPin'], config.value['authorityKeyPins'])
    require(installed['schemaVersion'] == 'RepositoryNativeInstallation/v2',
            'REPOSITORY_NATIVE_SOURCE_CURRENT_INSTALLATION_REQUIRED')
    peer = signed_pin(peer_pin, config.value['authorityKeyPins'])
    exact(peer, 'schemaVersion repositoryId sourceIdentityPin programPin ownerPythonPin ownerEntryPin ownerDependencyPins recipeTemplatePin assemblyTemplatePin sessionRoot custodyPaths resourceRoots sourceRoots sourceRootProofPins writerContainers dockerPin nftPin writerRulesSha256 readbackConfig signingKeyPin nativeImplementationPins executionHostPin labScopePin',
          'RepositoryNativePeerConfig/v2')
    require(peer['schemaVersion'] == 'RepositoryNativePeerConfig/v2' and
            peer['repositoryId'] == config.value['repositoryId'] and
            peer['sourceIdentityPin'] == config.policy['sourceIdentityPin'] and
            peer['executionHostPin'] == config.value['executionHostPin'] and
            peer['labScopePin'] == config.value['labScopePin'] and
            peer['programPin'] == config.implementation['nativePeer'] and
            peer['ownerPythonPin'] == host['pythonPin'] and
            peer['nativeImplementationPins'] == {role:config.implementation[role] for role in ROLES},
            'REPOSITORY_NATIVE_PEER_SCOPE_MISMATCH')
    source = dict(fields, repositoryId=config.value['repositoryId'],
        sourceIdentityPin=config.policy['sourceIdentityPin'], pythonPin=host['pythonPin'],
        nativePeerConfigPin=peer_pin, executionHostPin=config.value['executionHostPin'],
        resourceObserverPin=host['resourceObserverPin'])
    require(source['workspaceDirectory'] == str(config.root) and
            source['workspacePin']['path'] == str(config.root / 'workspace-config.json'),
            'REPOSITORY_NATIVE_SOURCE_SCOPE_MISMATCH')
    bootstrap = source['bootstrapBinding']
    require(type(bootstrap) is dict and set(bootstrap) == {'authorityKeyPin', 'ownerBinding'} and
            bootstrap['authorityKeyPin'] in config.value['authorityKeyPins'], 'REPOSITORY_LAB_BOOTSTRAP_INVALID')
    binding = bootstrap['ownerBinding']
    require(type(binding) is dict and set(binding) == {'releaseTag', 'attemptId', 'sourceContextSha256',
            'capturePolicySha256', 'nasWorkspaceConfigSha256'} and binding['releaseTag'] == LAB_ID and
            binding['sourceContextSha256'] == source['sourceIdentityPin']['sha256'] and
            bootstrap['ownerBinding']['nasWorkspaceConfigSha256'] == source['workspacePin']['sha256'],
            'REPOSITORY_LAB_BOOTSTRAP_INVALID')
    config.copy_protection()
    endpoint = signed_pin(signed_pin(config.policy['copyProtectionPin'], config.value['authorityKeyPins'])[
        'readbackEndpointEvidencePin'], config.value['authorityKeyPins'])
    readback_selection(peer['readbackConfig'], source, endpoint)
    arguments = ['-B', peer['programPin']['path'], '--service-configuration', service_pin['path'],
        '--service-sha256', service_pin['sha256'], '--configuration', peer_pin['path'],
        '--configuration-sha256', peer_pin['sha256']]
    for name in ('ownerCommand', 'nativeVerifierCommand'):
        selected = arguments + (['--launch'] if name == 'ownerCommand' else [])
        source[name] = dict(schemaVersion='RepositoryNativeCommand/v1', executablePin=host['pythonPin'],
            programPins=[peer['programPin']], arguments=selected, workingDirectory=host['workingDirectory'])
        command(source[name], host['pythonPin'], selected)
    stable_graph([source, service_pin], [], native_installation=installed)
    config.current()
    return source


def configure(config):
    exact(config.value, SERVICE_FIELDS, 'RepositoryNativeServiceConfig/v1')
    config.active_host_view = None
    from repository_host_view import select
    select(None)
    config.root = private(config.value['repositoryRoot'], directory=True)
    config.evidence = private(config.value['evidenceRoot'], directory=True)
    require(config.root != config.evidence and config.root not in config.evidence.parents and
            config.evidence not in config.root.parents, 'REPOSITORY_EVIDENCE_ROOT_OVERLAP')
    config.implementation = config.value['implementationPins']
    require(type(config.implementation) is dict and
            set(config.implementation) == set(ROLES) | {'captureBinder'}, 'REPOSITORY_NATIVE_IMPLEMENTATION_REQUIRED')
    for role, name in ROLES.items():
        pin = config.implementation[role]
        require(safe_path(pin['path']) == Path(__file__).absolute().with_name(name),
                'REPOSITORY_NATIVE_IMPLEMENTATION_LOCATION_CHANGED')
        private(pin['path']); read_pin(pin)
    for name in ('authorityKeyPins', 'evidenceKeyPins', 'captureBinderDependencyPins'):
        require(type(config.value[name]) is list and config.value[name], 'REPOSITORY_NATIVE_DEPENDENCIES_REQUIRED')
        for pin in config.value[name]:
            private(pin['path']); read_pin(pin, 32 * 1024 * 1024)
    require(type(config.value['recoveryApprovalPins']) is list, 'REPOSITORY_RECOVERY_APPROVAL_CONFIG_REQUIRED')
    config.schemas = document(read_pin(config.value['schemaPin']))
    config.policy = signed_pin(config.value['policyPin'], config.value['authorityKeyPins'])
    exact(config.policy, 'schemaVersion repositoryId sourceIdentityPin supportedVersionPins supportedToolPins maxChainPoints maxChainAgeSeconds retainNewestPoints minValidFullPoints retentionSeconds legalHoldPointPins copyProtectionPin', 'RepositoryPolicy/v1')
    require(config.policy['repositoryId'] == config.value['repositoryId'], 'REPOSITORY_POLICY_TARGET_MISMATCH')
    for key in ('maxChainPoints', 'maxChainAgeSeconds', 'retainNewestPoints', 'minValidFullPoints', 'retentionSeconds'):
        require(type(config.policy[key]) is int and config.policy[key] > 0, 'REPOSITORY_POLICY_REQUIRED')
    for key in ('supportedVersionPins', 'supportedToolPins', 'legalHoldPointPins'):
        require(type(config.policy[key]) is list, 'REPOSITORY_POLICY_REQUIRED')
        for pin in config.policy[key]: read_pin(pin)
    require(config.policy['supportedVersionPins'] and config.policy['supportedToolPins'], 'REPOSITORY_SUPPORTED_VERSIONS_REQUIRED')
    lab_scope(config)
    host = execution_host(config.value['executionHostPin'], config.value['authorityKeyPins'])
    installed=installation(host['installationManifestPin'],config.value['authorityKeyPins'])
    config.native_installation = installed if installed['schemaVersion'] == 'RepositoryNativeInstallation/v2' else None
    require(all(pin in installed['filePins'] for pin in config.implementation.values()) and
        all(pin in installed['filePins'] for pin in config.value['captureBinderDependencyPins']),
        'REPOSITORY_NATIVE_SERVICE_CLOSURE_NOT_INSTALLED')
    binder=config.implementation['captureBinder']
    require(Path(binder['path']).name=='formal_capture_recovery_inputs.py' and
        binder in config.value['captureBinderDependencyPins'], 'REPOSITORY_NATIVE_BINDER_NOT_SELECTED')
    approved={pin['path']:pin for pin in config.value['captureBinderDependencyPins']}
    for path in Path(binder['path']).parent.glob('*.py'):
        require(str(path) in approved, 'REPOSITORY_NATIVE_BINDER_DEPENDENCY_MISSING')
        private(path);read_pin(approved[str(path)])
    publisher = config.implementation['nativePublisher']
    command(config.value['publisherCommand'], host['pythonPin'], ['-B', publisher['path']])
    require(publisher in config.value['publisherCommand']['programPins'], 'REPOSITORY_NATIVE_PUBLISHER_NOT_SELECTED')


def current(config):
    read_pin(config.pin)
    read_pin(config.value['policyPin'])
    read_pin(config.value['schemaPin'])
    for pin in config.implementation.values(): read_pin(pin, 32 * 1024 * 1024)
    for name in ('authorityKeyPins', 'evidenceKeyPins', 'captureBinderDependencyPins', 'recoveryApprovalPins'):
        for pin in config.value[name]: read_pin(pin, 32 * 1024 * 1024)
    lab_scope(config)
    host = execution_host(config.value['executionHostPin'], config.value['authorityKeyPins'])
    installed = signed_pin(host['installationManifestPin'], config.value['authorityKeyPins'])
    config.native_installation = installed if installed['schemaVersion'] == 'RepositoryNativeInstallation/v2' else None


def selected_context(config):
    from repository_records import pin_file
    path = os.environ.get('INTRUOYI_REPOSITORY_LAB_CONTEXT_PATH')
    digest = os.environ.get('INTRUOYI_REPOSITORY_LAB_CONTEXT_SHA256')
    require(path is not None and digest is not None, 'REPOSITORY_LAB_CONTEXT_REQUIRED')
    pin = pin_file(path)
    require(pin['sha256'] == digest, 'REPOSITORY_LAB_CONTEXT_CHANGED')
    if hasattr(config, 'lab_context_pin'):
        require(config.lab_context_pin == pin, 'REPOSITORY_LAB_CONTEXT_SELECTION_CHANGED')
    config.lab_context_pin = pin
    return signed_pin(pin, config.value['authorityKeyPins'])


def launch_trust(config, source, request_pin):
    """Current W02 launch trust is selected after request, outside stable host."""
    from repository_records import pin_file
    path=os.environ.get('INTRUOYI_BACKUP_LAB_TRUST_PATH')
    digest=os.environ.get('INTRUOYI_BACKUP_LAB_TRUST_SHA256')
    require(path is not None and digest is not None,'REPOSITORY_LAB_LAUNCH_TRUST_REQUIRED')
    private(path);reference=pin_file(path)
    require(reference['sha256']==digest,'REPOSITORY_LAB_LAUNCH_TRUST_CHANGED')
    if hasattr(config,'lab_launch_trust_pin'):
        require(config.lab_launch_trust_pin==reference,'REPOSITORY_LAB_LAUNCH_TRUST_SELECTION_CHANGED')
    config.lab_launch_trust_pin=reference
    value=document(read_pin(reference))
    exact(value,'schemaVersion authorityKeyPin expectedContextPins hostBoundaryPin','backup-lab-launch-trust/v1')
    require(value['authorityKeyPin']==source['bootstrapBinding']['authorityKeyPin'] and
        value['expectedContextPins']==dict(sourceIdentityPin=source['sourceIdentityPin'],
            executionHostPin=source['executionHostPin'],labScopePin=config.value['labScopePin'],
            operationRequestPin=request_pin,installedClosurePin=document(read_pin(source['executionHostPin']))['installationManifestPin']),
        'REPOSITORY_LAB_LAUNCH_TRUST_MISMATCH')
    boundary=signed_pin(value['hostBoundaryPin'],[value['authorityKeyPin']])
    require(boundary['schemaVersion']=='backup-lab-native-host-boundary/v1' and
        boundary['executionHostPin']==source['executionHostPin'] and boundary['labScopePin']==config.value['labScopePin'],
        'REPOSITORY_LAB_LAUNCH_BOUNDARY_MISMATCH')
    return reference


def derive_owner(config, source, request_pin, recipe, assembly, save):
    """Instantiate explicit context-free templates; preserve their original Pins."""
    from repository_records import canonical
    context(config, source, request_pin)
    records = owner_template_records(config, source, document(read_pin(request_pin)), recipe, assembly)
    recipe, assembly = records['recipe'], records['assembly']
    # All originals and binding semantics are checked before the first write.
    for field, role in (('capture', 'capture-request'), ('resume', 'resume-request')):
        reference = save(records[field], role)
        require(document(read_pin(reference)) == records[field], 'REPOSITORY_LAB_DERIVED_ORIGINAL_CHANGED')
        assembly['captureRequestPin' if field == 'capture' else 'resumeRequestPin'] = reference
    reference = save(records['originalBinding'], 'release-binding')
    require(document(read_pin(reference)) == records['originalBinding'], 'REPOSITORY_LAB_DERIVED_ORIGINAL_CHANGED')
    assembly['inputReferences']['release_binding'] = reference
    assembly['binding']['originalReleaseBindingSha256'] = reference['sha256']
    return recipe, assembly


def claim_plan_bytes(value):
    """Exact FormalMaintenanceClaim plan encoding, including its final newline."""
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


def capture_asset_templates(object_binding, *, source_identity_pin, source_scope_pin,
                            reference_recipe_pin, derived_recipe_pin, version_pins,
                            point_type, parent_export_index_pin, policy_reasons,
                            policy_configuration_pins):
    """Author existing asset records from actual Pins, without runtime authority.

    Application owners author the reference/derived recipes. This configuration
    adapter preserves their bytes and contracts; the original native capture
    engine still observes SQL/binlog, objects, writers and the protected point.
    """
    require(type(object_binding) is dict and set(object_binding) == set(
        'sourceIdentity endpoint minioContainerId containerPort credentialReference buckets'.split()),
        'REPOSITORY_CAPTURE_OBJECT_BINDING_INVALID')
    require(point_type in ('FULL', 'INCREMENTAL') and
            (parent_export_index_pin is None) == (point_type == 'FULL'),
            'REPOSITORY_CAPTURE_PARENT_REQUIRED')
    identity = document(read_pin(source_identity_pin))
    scope = document(read_pin(source_scope_pin))
    reference = document(read_pin(reference_recipe_pin))
    derived = document(read_pin(derived_recipe_pin))
    exact(reference, 'schemaVersion sourceIdentity referenceQueries objectBindings maxRows complete coverageScopePin',
          'backup-capture-reference-recipe/v1')
    exact(derived, 'schemaVersion sourceIdentity classes', 'backup-capture-derived-recipe/v1')
    require(scope['sourceIdentityPin'] == source_identity_pin and
            reference['coverageScopePin'] == source_scope_pin and reference['complete'] is True and
            reference['sourceIdentity'] == derived['sourceIdentity'] == object_binding['sourceIdentity'] and
            identity['sourceFingerprint'] == object_binding['sourceIdentity'] and identity['databaseUuid'],
            'REPOSITORY_CAPTURE_ASSET_SOURCE_CHANGED')
    from urllib.parse import urlsplit
    require(urlsplit(object_binding['endpoint']).hostname in scope['endpointHosts'] and
            type(version_pins) is list and version_pins and
            type(object_binding['buckets']) is list and object_binding['buckets'],
            'REPOSITORY_CAPTURE_ASSET_SCOPE_INVALID')
    public_refs = [source_scope_pin, reference_recipe_pin, derived_recipe_pin, *version_pins]
    require(all(ref['path'] != object_binding['credentialReference']['path'] for ref in public_refs),
            'REPOSITORY_CAPTURE_PRIVATE_CREDENTIAL_AS_MATERIAL')
    for reference_pin in version_pins:
        document(read_pin(reference_pin))
    if parent_export_index_pin is not None:
        parent = document(read_pin(parent_export_index_pin, 64 * 1024 * 1024))
        require(parent['schemaVersion'] == 'backup-capture-object-index/v1' and
                parent['repositoryBound'] is True and parent['sourceIdentity'] == object_binding['sourceIdentity'],
                'REPOSITORY_CAPTURE_PARENT_INDEX_INVALID')
    require(set(derived['classes']) == set(policy_reasons) == set(policy_configuration_pins) == {'redis', 'queue'},
            'REPOSITORY_CAPTURE_DERIVED_POLICY_INVALID')
    policies = {}
    for name, item in derived['classes'].items():
        require(item['classification'] in ('REBUILD', 'NOT_PRESENT') and
                type(item['requiredForBusiness']) is bool and item['configurationReferences'] and
                type(policy_reasons[name]) is str and policy_reasons[name] and
                policy_configuration_pins[name] in item['configurationReferences'],
                'REPOSITORY_CAPTURE_DERIVED_POLICY_INVALID')
        if item['classification'] == 'REBUILD':
            require(type(item['executorKey']) is str and item['executorKey'] and
                    item['rebuildFrom'] in ('DATABASE', 'OBJECTS'),
                    'REPOSITORY_CAPTURE_DERIVED_POLICY_INVALID')
        else:
            require(item['requiredForBusiness'] is False and item['executorKey'] is None and
                    item['rebuildFrom'] is None, 'REPOSITORY_CAPTURE_DERIVED_POLICY_INVALID')
        for ref in item['configurationReferences']:
            require(ref['path'] != object_binding['credentialReference']['path'],
                    'REPOSITORY_CAPTURE_PRIVATE_CREDENTIAL_AS_MATERIAL')
            read_pin(ref)
        asset_class = 'mq' if name == 'queue' else name
        policies[asset_class] = dict(schemaVersion='backup-capture-ephemeral-policy/v1',
            **{'class': asset_class}, policy=item['classification'], reason=policy_reasons[name],
            configurationReference=policy_configuration_pins[name])
    return dict(objectSource=dict(schemaVersion='backup-capture-object-source/v1', **object_binding,
        sourceScopePin=source_scope_pin, referenceRecipePin=reference_recipe_pin,
        derivedRecipePin=derived_recipe_pin, versionPins=version_pins,
        parentExportIndexPin=parent_export_index_pin), ephemeralPolicies=policies)


def capture_asset_preflight(config, source, request, assembly):
    """Match the selected actual assets before launching the original owner."""
    series = document(read_pin(source['prepareRequestPin']))
    exact(series, 'schemaVersion backupId generationId pointType catalogPin parentPointPin parentRepositoryPointPin',
          'backup-capture-series/v1')
    require(request['action'] in ('BACKUP_FULL', 'BACKUP_INCREMENTAL'), 'REPOSITORY_CAPTURE_ACTION_INVALID')
    point_type = {'BACKUP_FULL': 'FULL', 'BACKUP_INCREMENTAL': 'INCREMENTAL'}[request['action']]
    require(series['pointType'] == point_type, 'REPOSITORY_CAPTURE_ACTION_CHANGED')
    if point_type == 'FULL':
        require(request['selectedPointPin'] is None and series['parentPointPin'] is None and
                series['parentRepositoryPointPin'] is None, 'REPOSITORY_CAPTURE_FULL_PARENT_FORBIDDEN')
        parent_index_pin = None
    else:
        from repository_catalog import Catalog
        catalog = Catalog(config, Deadline(request['deadlineMilliseconds']))
        catalog.chain(request['selectedPointPin'])
        parent_binding = catalog.binding(request['selectedPointPin'])
        material = document(read_pin(parent_binding['recoveryMaterialPin'], 64 * 1024 * 1024))
        parent_index_pin = parent_binding['objectContentIndexPin']
        parent_index = document(read_pin(parent_index_pin, 64 * 1024 * 1024))
        read_pin(material['database']['capturePointPin'], 64 * 1024 * 1024, catalog.deadline)
        require(series['parentRepositoryPointPin'] == request['selectedPointPin'] and
                series['parentPointPin'] == material['database']['capturePointPin'] and
                series['generationId'] == parent_index['generationId'],
                'REPOSITORY_CAPTURE_PARENT_CHANGED')
    catalog = document(read_pin(series['catalogPin']))
    exact(catalog, 'schemaVersion sourceIdentity assets writers rtoMilliseconds rpoMilliseconds stopWindowMilliseconds sourceLogicalBytes temporaryPeakBytes',
          'backup-capture-catalog/v1')
    assets = {}
    for item in catalog['assets']:
        require(item['assetId'] not in assets, 'REPOSITORY_CAPTURE_ASSET_DUPLICATE')
        assets[item['assetId']] = item
        read_pin(item['reference'])
    def asset(asset_class):
        matches = [item for item in assets.values() if item['class'] == asset_class]
        require(len(matches) == 1, 'REPOSITORY_CAPTURE_ASSET_COVERAGE_REQUIRED')
        return matches[0]
    for writer in catalog['writers']:
        read_pin(writer['protectionReference'])
    object_source = document(read_pin(asset('objects')['reference']))
    require(all(pin in config.policy['supportedVersionPins'] for pin in object_source['versionPins']),
            'REPOSITORY_CAPTURE_VERSION_NOT_SUPPORTED')
    binding = document(read_pin(assembly['catalogBindingPin']))
    capture = document(read_pin(assembly['captureRequestPin']))
    require(binding['assetReferences'] == catalog['assets'] and binding['writerReferences'] == catalog['writers'] and
            binding['sourceIdentity'] == catalog['sourceIdentity'] == object_source['sourceIdentity'] and
            binding['databaseName'] == capture['database'] and binding['binlogDatabaseScope'] == [capture['database']] and
            binding['minioContainerId'] == capture['claimBinding']['minioContainerId'] == object_source['minioContainerId'],
            'REPOSITORY_CAPTURE_CATALOG_BINDING_CHANGED')
    reasons = {}; policy_configuration_pins = {}
    policies = {}
    for name, asset_class in (('redis', 'redis'), ('queue', 'mq')):
        item = asset(asset_class)
        policy = document(read_pin(item['reference']))
        reasons[name] = policy['reason']
        policy_configuration_pins[name] = policy['configurationReference']
        require(item['policy'] == policy['policy'], 'REPOSITORY_CAPTURE_DERIVED_POLICY_CHANGED')
        policies[asset_class] = policy
    records = capture_asset_templates(
        {k: object_source[k] for k in ('sourceIdentity', 'endpoint', 'minioContainerId', 'containerPort', 'credentialReference', 'buckets')},
        source_identity_pin=source['sourceIdentityPin'], source_scope_pin=object_source['sourceScopePin'],
        reference_recipe_pin=object_source['referenceRecipePin'], derived_recipe_pin=object_source['derivedRecipePin'],
        version_pins=object_source['versionPins'], point_type=point_type,
        parent_export_index_pin=parent_index_pin, policy_reasons=reasons,
        policy_configuration_pins=policy_configuration_pins)
    require(records['objectSource'] == object_source and records['ephemeralPolicies'] == policies,
            'REPOSITORY_CAPTURE_ASSET_CONFIGURATION_CHANGED')
    return records


def owner_template_records(config, source, request, recipe, assembly):
    """Pure late-record derivation from re-read originals; never writes templates."""
    from repository_records import canonical
    recipe = document(canonical(recipe)); assembly = document(canonical(assembly))
    require(recipe['schemaVersion']=='backup-lab-normal-owner-recipe-template/v1' and
        assembly['schemaVersion']=='backup-lab-native-assembly-template/v1' and
        'labContextPin' not in recipe and 'labContextPin' not in assembly,
        'REPOSITORY_LAB_STABLE_OWNER_TEMPLATE_REQUIRED')
    stable_graph([recipe,assembly], [config.lab_context_pin],
                 native_installation=getattr(config, 'native_installation', None))
    require(source['prepareRequestPin']==assembly['seriesPin'] and
        source['captureRequestPin']==assembly['captureRequestPin'], 'REPOSITORY_LAB_OWNER_TEMPLATE_NOT_SELECTED')
    capture=document(read_pin(assembly['captureRequestPin']))
    require(capture['schemaVersion']=='backup-lab-capture-request-template/v1' and
        'labContextPin' not in capture and 'labContextPin' not in capture['sourceScope'] and
        capture['sourceScope']['schemaVersion']=='backup-lab-source-scope-template/v1',
        'REPOSITORY_LAB_STABLE_CAPTURE_TEMPLATE_REQUIRED')
    capture['schemaVersion']='backup-lab-capture-request/v1'
    capture['labContextPin']=config.lab_context_pin
    scope=capture['sourceScope']
    scope['schemaVersion']='backup-lab-source-scope/v1';scope['labContextPin']=config.lab_context_pin
    resume=document(read_pin(assembly['resumeRequestPin']))
    exact(resume,'schemaVersion','backup-lab-resume-template/v1')
    resume=dict(schemaVersion='backup-lab-resume-request/v1', labContextPin=config.lab_context_pin)
    release=document(read_pin(assembly['inputReferences']['release_binding']))
    exact(release,'schemaVersion rehearsalId claimBindingSha256 approvedSourceTargetSha256 productionEvidence',
        'backup-lab-original-package-binding-template/v1')
    exact(scope,'schemaVersion environment targetRawSha256 targetFingerprint database databaseUuid labContextPin',
        'backup-lab-source-scope/v1')
    identity = document(read_pin(source['sourceIdentityPin']))
    claim = recipe['claimBinding']
    claim_sha = hashlib.sha256(claim_plan_bytes(claim)).hexdigest()
    require(recipe['claimRoot'] == capture['claimRoot'] and claim == capture['claimBinding'] and
        claim['operationId'] == request['operationId'] and
        claim['sourceFingerprint'] == identity['sourceFingerprint'] == scope['targetFingerprint'] and
        claim['databaseUuid'] == identity['databaseUuid'] == scope['databaseUuid'] and
        scope['environment'] == 'backup-lab' and scope['database'] == capture['database'] and
        release['rehearsalId'] == LAB_ID and release['productionEvidence'] is False and
        release['claimBindingSha256'] == assembly['binding']['claimBindingSha256'] == claim_sha,
        'REPOSITORY_LAB_CLAIM_BINDING_CHANGED')
    require(assembly['inputReferences']['source_context']==source['sourceIdentityPin'] and
        assembly['inputReferences']['installed_context']==source['executionHostPin'] and
        assembly['binding']['releaseTag']==LAB_ID and
        assembly['binding']['sourceContextSha256']==source['sourceIdentityPin']['sha256'] and
        assembly['binding']['installedContextSha256']==source['executionHostPin']['sha256'] and
        assembly['binding']['nasWorkspaceConfigSha256']==source['workspacePin']['sha256'],
        'REPOSITORY_LAB_STABLE_BINDING_CHANGED')
    catalog=document(read_pin(assembly['catalogBindingPin']))
    require(catalog['schemaVersion']=='backup-native-catalog-binding/v1', 'REPOSITORY_LAB_CATALOG_SCHEMA_INVALID')
    require(catalog['sharedScopeSha256']==capture['sharedScopeSha256'], 'REPOSITORY_LAB_SHARED_SCOPE_CHANGED')
    target = catalog['approvedSourceTargetPin']; read_pin(target)
    require(release['approvedSourceTargetSha256'] == scope['targetRawSha256'] == target['sha256'] and
        source['bootstrapBinding']['ownerBinding'] == {k:assembly['binding'][k] for k in
            ('releaseTag','attemptId','sourceContextSha256','capturePolicySha256','nasWorkspaceConfigSha256')},
        'REPOSITORY_LAB_STABLE_BINDING_CHANGED')
    release['schemaVersion']='backup-lab-original-package-binding/v1';release['labContextPin']=config.lab_context_pin
    recipe['schemaVersion']='backup-lab-normal-owner-recipe/v1';recipe['labContextPin']=config.lab_context_pin
    assembly['schemaVersion']='backup-lab-native-assembly-config/v1';assembly['labContextPin']=config.lab_context_pin
    return dict(recipe=recipe, assembly=assembly, capture=capture, resume=resume, originalBinding=release)


def context(config, source, request_pin):
    bootstrap = source['bootstrapBinding']
    require(type(bootstrap) is dict and set(bootstrap) == {'authorityKeyPin', 'ownerBinding'},
            'REPOSITORY_LAB_BOOTSTRAP_INVALID')
    owner_binding=bootstrap['ownerBinding']
    require(type(owner_binding) is dict and set(owner_binding)=={'releaseTag','attemptId',
        'sourceContextSha256','capturePolicySha256','nasWorkspaceConfigSha256'} and
        owner_binding['releaseTag']==LAB_ID and owner_binding['sourceContextSha256']==source['sourceIdentityPin']['sha256'] and
        owner_binding['nasWorkspaceConfigSha256']==source['workspacePin']['sha256'], 'REPOSITORY_LAB_BOOTSTRAP_INVALID')
    value = selected_context(config)
    selected = config.lab_context_pin
    private(selected['path'])
    exact(value, 'schemaVersion rehearsalId environment sourceIdentityPin executionHostPin labScopePin operationRequestPin installedClosurePin authorizationPin leasePin authorityKeyPin issuedAt expiresAt',
          'BackupRehearsalAuthorityContext/v1')
    request = document(read_pin(request_pin))
    host = execution_host(config.value['executionHostPin'], config.value['authorityKeyPins'])
    installed = signed_pin(host['installationManifestPin'], config.value['authorityKeyPins'])
    native = installed if installed['schemaVersion'] == 'RepositoryNativeInstallation/v2' else None
    stable_graph([request, config.pin], [selected, request_pin], native_installation=native)
    now = datetime.now(timezone.utc)
    require(value['rehearsalId'] == LAB_ID and value['environment'] == 'backup-lab' and
            value['sourceIdentityPin'] == config.policy['sourceIdentityPin'] == source['sourceIdentityPin'] and
            value['executionHostPin'] == config.value['executionHostPin'] == source['executionHostPin'] and
            value['labScopePin'] == config.value['labScopePin'] and value['operationRequestPin'] == request_pin and
            value['installedClosurePin'] == host['installationManifestPin'] and
            value['authorizationPin'] in request['authorizationRefs'] and value['leasePin'] == request['leaseRef'] and
            value['authorityKeyPin'] in config.value['authorityKeyPins'] and
            bootstrap['authorityKeyPin'] == value['authorityKeyPin'] and
            timestamp(value['issuedAt']) <= now < timestamp(value['expiresAt']), 'REPOSITORY_LAB_CONTEXT_MISMATCH')
    envelope = document(read_pin(selected))
    require(envelope['keySha256'] == value['authorityKeyPin']['sha256'], 'REPOSITORY_LAB_CONTEXT_SIGNER_MISMATCH')
    operation_authority(config, source, request, value, now)
    for name in ('sourceIdentityPin', 'installedClosurePin', 'authorityKeyPin'): read_pin(value[name], 128 * 1024 * 1024)
    lab_scope(config, request)
    return value


def operation_authority(config, source, request, value, now):
    """Verify actual signed grant/lease for this action and repository."""
    grant = signed_pin(value['authorizationPin'], config.value['authorityKeyPins'])
    exact(grant, 'schemaVersion repositoryId operationId actions sourceOrTargetRef policyPin resourcePin notBefore expiresAt leaseRef',
        'RepositoryAuthorization/v1')
    require(type(grant['actions']) is list and grant['actions'] and
            all(type(action) is str for action in grant['actions']) and
            len(set(grant['actions'])) == len(grant['actions']) and set(grant['actions']) <= LAB_ACTIONS and
            source['schemaVersion'] == 'RepositoryNativeBackupSource/v1' and
            source['repositoryId'] == config.value['repositoryId'] == config.policy['repositoryId'] == grant['repositoryId'] and
            grant['operationId'] == request['operationId'] and request['action'] in grant['actions'] and
            grant['sourceOrTargetRef'] == request['sourceOrTargetRef'] and grant['resourcePin'] == request['sourceOrTargetRef'] and
            grant['policyPin'] == request['policyPin'] and grant['leaseRef'] == value['leasePin'] and
            timestamp(grant['notBefore']) <= now < timestamp(grant['expiresAt']), 'REPOSITORY_LAB_CONTEXT_GRANT_INVALID')
    lease = signed_pin(value['leasePin'], config.value['authorityKeyPins'])
    exact(lease, 'schemaVersion repositoryId operationId ownerIdentityPin expiresAt', 'RepositoryLease/v1')
    require(lease['repositoryId'] == grant['repositoryId'] and lease['operationId'] == request['operationId'] and timestamp(lease['expiresAt']) > now,
            'REPOSITORY_LAB_CONTEXT_LEASE_INVALID')
    read_pin(lease['ownerIdentityPin'])
    lab_scope(config, request)
    return lease


def copy_protection(config):
    proof = signed_pin(config.policy['copyProtectionPin'], config.value['authorityKeyPins'])
    exact(proof, 'schemaVersion repositoryId sourceIdentityPin labScopePin sourceDeletionDenied independentFailureDomain recoveryKeysAvailable aclEvidencePin readbackEndpointEvidencePin validUntil', 'RepositoryLabCopyProtection/v1')
    require(proof['repositoryId'] == config.value['repositoryId'] and
            proof['sourceIdentityPin'] == config.policy['sourceIdentityPin'] and proof['labScopePin'] == config.value['labScopePin'] and
            proof['independentFailureDomain'] is False and proof['sourceDeletionDenied'] is True and
            proof['recoveryKeysAvailable'] is True and timestamp(proof['validUntil']) > datetime.now(timezone.utc),
            'REPOSITORY_LAB_COPY_PROTECTION_UNPROVEN')
    lab_scope(config)
    acl = signed_pin(proof['aclEvidencePin'], config.value['authorityKeyPins'])
    endpoint = signed_pin(proof['readbackEndpointEvidencePin'], config.value['authorityKeyPins'])
    exact(acl, 'schemaVersion labScopePin sourceIdentityPin archiveRoot sourceAccountPin writerAccountPin readerAccountPin deletionAttemptPin keyAccessEvidencePin', 'RepositoryLabAclEvidence/v1')
    exact(endpoint, 'schemaVersion labScopePin archiveRoot uncRoot encrypted signingRequired independentConnectionId readerAccountPin readbackOriginalPin observedAt', 'RepositoryLabReadbackEndpoint/v1')
    require(acl['labScopePin'] == endpoint['labScopePin'] == proof['labScopePin'] and
            acl['sourceIdentityPin'] == proof['sourceIdentityPin'] and acl['archiveRoot'] == endpoint['archiveRoot'] and
            acl['archiveRoot'] == str(config.root/'archives') and
            acl['readerAccountPin'] == endpoint['readerAccountPin'] and
            len({p['sha256'] for p in (acl['sourceAccountPin'], acl['writerAccountPin'], acl['readerAccountPin'])}) == 3 and
            endpoint['encrypted'] is True and endpoint['signingRequired'] is True and
            type(endpoint['independentConnectionId']) is str and endpoint['independentConnectionId'],
            'REPOSITORY_LAB_ACL_READBACK_UNPROVEN')
    contained(acl['archiveRoot'])
    deletion = signed_pin(acl['deletionAttemptPin'], config.value['authorityKeyPins'])
    keys = signed_pin(acl['keyAccessEvidencePin'], config.value['authorityKeyPins'])
    exact(deletion, 'schemaVersion labScopePin accountPin archiveRoot deleteDenied probeOriginalPin', 'RepositoryLabDeletionProbe/v1')
    exact(keys, 'schemaVersion labScopePin recoveryKeysAvailable probeOriginalPin', 'RepositoryLabKeyAccess/v1')
    require(deletion.get('schemaVersion') == 'RepositoryLabDeletionProbe/v1' and
            deletion.get('labScopePin') == proof['labScopePin'] and deletion.get('accountPin') == acl['sourceAccountPin'] and
            deletion.get('archiveRoot') == acl['archiveRoot'] and deletion.get('deleteDenied') is True and
            deletion.get('probeOriginalPin') is not None and
            keys.get('schemaVersion') == 'RepositoryLabKeyAccess/v1' and keys.get('labScopePin') == proof['labScopePin'] and
            keys.get('recoveryKeysAvailable') is True and keys.get('probeOriginalPin') is not None,
            'REPOSITORY_LAB_ORIGINAL_PROBES_REQUIRED')
    for pin in (deletion['probeOriginalPin'], keys['probeOriginalPin'], endpoint['readbackOriginalPin'],
                acl['sourceAccountPin'], acl['writerAccountPin'], acl['readerAccountPin']): read_pin(pin)
    return config.policy['copyProtectionPin']
