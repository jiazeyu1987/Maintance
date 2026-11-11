"""Typed MAIN material publication; archive proof grants no clear permission.

Ordinary repository points and their original-process exit contract are not
interpreted here. Dedicated preservation points retain the current target while
its real capture context and original writer protections remain held.
"""
from copy import deepcopy
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import time
from types import SimpleNamespace

from recovery_engine import RecoveryError
from recovery_archive_guard import ArchivePathGuard
from recovery_backup_epoch import _path, _read_file
from recovery_program_native import _NativeView
from recovery_replacement_storage import parse_mountinfo as _parse_mountinfo, visible_mount as _visible_mount
from minimal_capture_support import actual_pin, exclusive_json
from repository_records import (RepositoryError, canonical, document, exact,
    require, utc, validate_pin)

ROLE = 'TARGET_PRE_RESTORE'
POLICY = ('schemaVersion targetConfigRef captureRef captureConfigurationPin '
    'repositoryConfigurationPin backupEpochPolicy maxArchiveBytes '
    'maxReadbackRecordBytes maxPreservationSeconds minimumFreeBytes')
REPOSITORY = ('schemaVersion repositoryId repositoryRoot sourceIdentityPin '
    'captureBinderPin readbackConfigPin')
REPOSITORY_V2 = ('schemaVersion repositoryId repositoryRoot sourceIdentityPin '
    'captureBinderPin readbackTemplatePin writeView')
READBACK_TEMPLATE = ('schemaVersion uncRoot repositoryRelativePath repositoryRoot credentialPin '
    'port authProtocol maximumRecordBytes maximumTotalRecordBytes libraryPins recordRootPolicy')
READBACK_ROOT_POLICY = 'CURRENT_OPERATION_TARGET_PRESERVATION_PUBLICATION'
HOLD_INTENT = ('schemaVersion repositoryId operationId targetConfigRef role '
    'archivePath pointPath preservationIntentPin createdAt')
HOLD = ('schemaVersion repositoryId operationId targetConfigRef role intentPin '
    'pointPin archiveProofPin createdAt')
PROOF = ('schemaVersion state operationId targetConfigRef role intentPin '
    'materialsPin holdIntentPin pointPin manifestPin payloadTreePin '
    'repositoryBindingPin recoveryMaterialPin objectContentIndexPin readbackPin '
    'sidecarReadbackPin archiveClosePin captureTerminalPin payloadContentVerified '
    'serverDurabilityVerified independentFailureDomain originalResultPins finishedAt')
POINT = ('schemaVersion role backupId generationId pointType parentPointPins '
    'commonRecoveryPoint payloadRefs manifestPin readbackEvidencePin '
    'archiveCloseEvidencePin captureTerminalEvidencePin integrityState controlledRestoreEligible')


def _read(reference, limit=4*1024*1024):
    validate_pin(reference)
    raw, observed = _read_file(reference['path'], limit)
    require(observed == reference, 'PRESERVATION_INPUT_CHANGED')
    return raw


def _json(reference, limit=4*1024*1024):
    return document(_read(reference, limit))


def _new(path, value):
    # Repository manifests use the existing repository canonical format; the
    # capture journal's canonical format intentionally has a different newline.
    path = _path(str(path)); raw = canonical(value)
    require(0 < len(raw) <= 64*1024*1024, 'PRESERVATION_DOCUMENT_LIMIT')
    fd = os.open(path, os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    directory = os.open(path.parent, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(directory)
    finally:os.close(directory)
    reference = actual_pin(path)
    require(reference['bytes'] == len(raw) and reference['sha256'] == hashlib.sha256(raw).hexdigest(),
        'PRESERVATION_INPUT_CHANGED')
    return reference


def _directory(path):
    path = _path(str(path))
    value = path.lstat()
    require(path.is_dir() and value.st_uid == os.geteuid() and not value.st_mode & 0o022,
        'PRESERVATION_DIRECTORY_INVALID')
    return value.st_dev, value.st_ino


def _operation(value):
    require(type(value) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,120}', value),
        'PRESERVATION_OPERATION_INVALID')
    return value


def _posix(value):
    require(type(value) is str and value.startswith('/') and not value.startswith('//') and
        '\\' not in value and not any(ord(c)<32 for c in value) and
        str(PurePosixPath(value))==value and '..' not in PurePosixPath(value).parts and value!='/',
        'PRESERVATION_WRITE_VIEW_INVALID')
    return value


def _template_configuration(repository, template, policy, operation_root):
    """Validate only stable declarations; this grants no filesystem admission."""
    require(type(template) is dict and set(template)==set(READBACK_TEMPLATE.split()) and
        template.get('schemaVersion')=='MainTargetPreservationReadbackTemplate/v1' and
        template.get('recordRootPolicy')==READBACK_ROOT_POLICY,
        'PRESERVATION_READBACK_TEMPLATE_INVALID')
    root=_posix(repository['repositoryRoot'])
    require(template['repositoryRoot']==root,'PRESERVATION_READBACK_SCOPE_CHANGED')
    from repository_native_readback import relative_name
    relative=relative_name(template['repositoryRelativePath'])
    unc=template['uncRoot']
    require(type(unc) is str and re.fullmatch(r'\\\\[^\\/:*?"<>|\x00-\x20]+\\[^\\/:*?"<>|\x00-\x1f]+',unc) and
        all(part.rstrip(' .')==part for part in unc[2:].split('\\')),
        'PRESERVATION_READBACK_TEMPLATE_INVALID')
    view=repository['writeView']
    require(type(view) is dict and set(view)=={'mountPoint','filesystem','mountSource','mountRoot'} and
        view['filesystem']=='cifs' and view['mountPoint']==root and
        view['mountSource']=='//'+unc[2:].replace('\\','/') and
        view['mountRoot']=='/'+relative,'PRESERVATION_WRITE_VIEW_INVALID')
    _posix(view['mountRoot'])
    require(type(template['port']) is int and 1<=template['port']<=65535 and
        template['authProtocol'] in ('ntlm','kerberos') and
        type(template['maximumRecordBytes']) is int and 0<template['maximumRecordBytes']<=64*1024*1024 and
        type(template['maximumTotalRecordBytes']) is int and
        template['maximumRecordBytes']<=template['maximumTotalRecordBytes']<=policy['maxReadbackRecordBytes'] and
        type(template['libraryPins']) is list and 0<len(template['libraryPins'])<=1000,
        'PRESERVATION_READBACK_TEMPLATE_INVALID')
    validate_pin(template['credentialPin'])
    for reference in template['libraryPins']:validate_pin(reference)
    result={key:deepcopy(value) for key,value in template.items()
        if key not in ('schemaVersion','recordRootPolicy')}
    result.update(schemaVersion='RepositorySmbReadbackConfig/v1',
        recordRoot=str(operation_root/'target-preservation'/'publication'))
    return result


def _v2_inputs(native, policy_pin):
    view=getattr(native,'native_context',None)
    require(type(view) is _NativeView and view.phase=='PREPARATION',
        'PRESERVATION_PREPARATION_REQUIRED')
    view.guard_native(native);context=view._context
    target=context._request['targetConfigRef']
    require(context._owner.get('targetPreservationPolicies',{}).get(target)==policy_pin,
        'PRESERVATION_POLICY_UNREGISTERED')
    policy=_json(policy_pin);exact(policy,POLICY,'MainTargetPreservationPolicy/v2')
    require(policy['targetConfigRef']==target and
        context._policy['captureConfigurationPins'].get(policy['captureRef'])==policy['captureConfigurationPin'] and
        policy['backupEpochPolicy']==context._policy['backupEpochPolicy'],'PRESERVATION_POLICY_SCOPE_CHANGED')
    require(all(type(policy[k]) is int and policy[k]>0 for k in
        ('maxArchiveBytes','maxReadbackRecordBytes','maxPreservationSeconds','minimumFreeBytes')),
        'PRESERVATION_BUDGET_INVALID')
    capture=_json(policy['captureConfigurationPin'])
    require(capture.get('schemaVersion')=='MainTargetCaptureConfiguration/v1' and
        capture.get('outputRootPolicy')=='CURRENT_OPERATION_TARGET_PRESERVATION_CAPTURE' and
        capture.get('parent') is None,'PRESERVATION_MAIN_CAPTURE_CONFIGURATION_REQUIRED')
    from minimal_capture_support import validate_main_target_config
    validate_main_target_config(capture)
    repository=_json(policy['repositoryConfigurationPin'])
    exact(repository,REPOSITORY_V2,'MainTargetPreservationRepository/v2')
    require(type(repository['repositoryId']) is str and repository['repositoryId'],
        'PRESERVATION_REPOSITORY_INVALID')
    template=_json(repository['readbackTemplatePin'])
    configuration=_template_configuration(repository,template,policy,context._root)
    return context,policy,repository,configuration


def _derive_readback_configuration(native, *, policy_pin):
    """Create private per-operation originals, never a writable-view capability."""
    context,policy,repository,configuration=_v2_inputs(native,policy_pin)
    from recovery_program_protection import _preservation_root
    root=_preservation_root(context)/'publication'
    require(not os.path.lexists(root),'PRESERVATION_READBACK_ALREADY_DERIVED')
    root.mkdir(mode=0o700)
    configuration_pin=_new(root/'readback-configuration.json',configuration)
    native.original_pins.append(deepcopy(configuration_pin))
    derivation_pin=_new(root/'readback-derivation.json',dict(
        schemaVersion='MainTargetPreservationReadbackDerivation/v1',
        operationId=context._request['operationId'],targetConfigRef=context._request['targetConfigRef'],
        policyPin=policy_pin,repositoryConfigurationPin=policy['repositoryConfigurationPin'],
        templatePin=repository['readbackTemplatePin'],executionBindingPin=context._binding,
        operationRoot=str(context._root),configurationPin=configuration_pin))
    native.original_pins.append(deepcopy(derivation_pin))
    return dict(configurationPin=configuration_pin,derivationPin=derivation_pin)


class _WriteViewLease:
    """Hold the actual view FD; privileged forced unmount is not atomic with writes."""
    def __init__(self, repository):
        self._closed=False;self._fd=None
        self._expected=deepcopy(repository['writeView'])
        self._path=_path(repository['repositoryRoot'])
        try:
            self._fd=os.open(self._path,os.O_PATH|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
            self.observation=self._observe()
        except BaseException:
            self.close();raise

    def _observe(self):
        require(not self._closed,'PRESERVATION_WRITE_VIEW_CLOSED')
        _directory(self._path)
        held=os.fstat(self._fd);current=self._path.stat()
        identity=lambda info:dict(device=info.st_dev,inode=info.st_ino,mode=stat.S_IMODE(info.st_mode),
            uid=info.st_uid,gid=info.st_gid)
        require(stat.S_ISDIR(held.st_mode) and identity(held)==identity(current),
            'PRESERVATION_WRITE_VIEW_DIRECTORY_CHANGED')
        raw=Path('/proc/self/mountinfo').read_text(encoding='utf-8')
        rows=_parse_mountinfo(raw);observed=_visible_mount(str(self._path),rows)
        require(observed['filesystem']=='cifs','PRESERVATION_WRITE_VIEW_CIFS_REQUIRED')
        require(all(observed[key]==value for key,value in
            (('mountPoint',self._expected['mountPoint']),('source',self._expected['mountSource']),
             ('root',self._expected['mountRoot']))),'PRESERVATION_WRITE_VIEW_MOUNT_MISMATCH')
        require(all('rw' in observed[key] and 'ro' not in observed[key] for key in ('options','superOptions')),
            'PRESERVATION_WRITE_VIEW_READ_ONLY')
        ids=re.findall(r'^mnt_id:\s*([0-9]+)\s*$',
            Path('/proc/self/fdinfo',str(self._fd)).read_text(encoding='ascii'),re.MULTILINE)
        require(len(ids)==1 and int(ids[0])==observed['mountId'] and
            observed['device']==str(os.major(held.st_dev))+':'+str(os.minor(held.st_dev)),
            'PRESERVATION_WRITE_VIEW_MOUNT_MISMATCH')
        require(not any(self._path in Path(row['mountPoint']).parents for row in rows),
            'PRESERVATION_WRITE_VIEW_NESTED_MOUNT')
        lines=[line for line in raw.splitlines() if line.split(' ',1)[0]==str(observed['mountId'])]
        require(len(lines)==1,'PRESERVATION_WRITE_VIEW_MOUNT_MISMATCH')
        return dict(mountIdentity=observed,rootIdentity=identity(held),mountInfoLine=lines[0])

    def check(self):
        try:
            require(self._observe()==self.observation,'PRESERVATION_WRITE_VIEW_CHANGED')
        except BaseException as error:
            # Admission has already happened. Any later mismatch prohibits clear.
            raise RepositoryError('PRESERVATION_WRITE_VIEW_CHANGED',unknown=True) from error

    def close(self):
        if self._closed:return
        self._closed=True
        if self._fd is not None:os.close(self._fd);self._fd=None


@contextmanager
def _preparation_view_guard(context, lease):
    """Bounded preparation custody until the publication owns resource checks."""
    if lease is None:
        yield
        return
    previous=context._outer_guard
    def guarded():
        if previous is not None:previous()
        lease.check()
    context._outer_guard=guarded
    try:
        yield
    finally:
        if context._outer_guard is not guarded:
            # Do not overwrite a guard owned by somebody else or lose the
            # original exception; Python retains it as the chained context.
            raise RepositoryError('PRESERVATION_PREPARATION_GUARD_CHANGED',unknown=True)
        context._outer_guard=previous


def _read_v2_admission(reader, *, policy_pin,policy,repository,request,root,binding_pin,derivation_pin,view_pin):
    """Consume original declarations and that operation's observation, not live mounts."""
    exact(policy,POLICY,'MainTargetPreservationPolicy/v2')
    exact(repository,REPOSITORY_V2,'MainTargetPreservationRepository/v2')
    operation=request['operationId'];target=request['targetConfigRef']
    publication=root/'target-preservation'/'publication'
    def fixed(reference,path):
        require(_path(reference['path'])==path,'PRESERVATION_EVIDENCE_PATH_CHANGED')
        return reader.read(reference)
    template=reader.read(repository['readbackTemplatePin'])
    expected=_template_configuration(repository,template,policy,root)
    derivation=fixed(derivation_pin,publication/'readback-derivation.json')
    require(type(derivation) is dict and set(derivation)=={'schemaVersion','operationId','targetConfigRef',
        'policyPin','repositoryConfigurationPin','templatePin','executionBindingPin','operationRoot','configurationPin'} and
        derivation['schemaVersion']=='MainTargetPreservationReadbackDerivation/v1' and
        derivation['operationId']==operation and derivation['targetConfigRef']==target and
        derivation['policyPin']==policy_pin and derivation['repositoryConfigurationPin']==policy['repositoryConfigurationPin'] and
        derivation['templatePin']==repository['readbackTemplatePin'] and derivation['executionBindingPin']==binding_pin and
        derivation['operationRoot']==str(root),'PRESERVATION_READBACK_DERIVATION_CHANGED')
    require(fixed(derivation['configurationPin'],publication/'readback-configuration.json')==expected,
        'PRESERVATION_READBACK_DERIVATION_CHANGED')
    observed=fixed(view_pin,root/'target-preservation'/'write-view.json')
    require(type(observed) is dict and set(observed)=={'schemaVersion','operationId','targetConfigRef',
        'repositoryConfigurationPin','executionBindingPin','mountIdentity','rootIdentity','mountInfoLine','observedAt'} and
        observed['schemaVersion']=='MainTargetPreservationWriteViewObservation/v1' and
        observed['operationId']==operation and observed['targetConfigRef']==target and
        observed['repositoryConfigurationPin']==policy['repositoryConfigurationPin'] and
        observed['executionBindingPin']==binding_pin,'PRESERVATION_WRITE_VIEW_EVIDENCE_CHANGED')
    line=observed['mountInfoLine']
    require(type(line) is str and 0<len(line)<=65536 and '\n' not in line and '\r' not in line,
        'PRESERVATION_WRITE_VIEW_EVIDENCE_CHANGED')
    rows=_parse_mountinfo(line)
    require(len(rows)==1 and rows[0]==observed['mountIdentity'],'PRESERVATION_WRITE_VIEW_EVIDENCE_CHANGED')
    mount=rows[0];view=repository['writeView'];identity=observed['rootIdentity']
    require(mount['filesystem']=='cifs','PRESERVATION_WRITE_VIEW_CIFS_REQUIRED')
    require(mount['mountPoint']==view['mountPoint'] and mount['source']==view['mountSource'] and
        mount['root']==view['mountRoot'] and
        all('rw' in mount[key] and 'ro' not in mount[key] for key in ('options','superOptions')),
        'PRESERVATION_WRITE_VIEW_EVIDENCE_CHANGED')
    require(type(identity) is dict and set(identity)=={'device','inode','mode','uid','gid'} and
        all(type(value) is int and value>=0 for value in identity.values()) and identity['inode']>0 and
        identity['mode']<=0o7777 and not identity['mode']&0o022 and
        mount['device']==str(os.major(identity['device']))+':'+str(os.minor(identity['device'])) and
        type(observed['observedAt']) is str and
        re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)',observed['observedAt']),
        'PRESERVATION_WRITE_VIEW_EVIDENCE_CHANGED')
    return dict(configurationPin=deepcopy(derivation['configurationPin']),
        derivationPin=deepcopy(derivation_pin),writeViewObservationPin=deepcopy(view_pin))


def _location(root, operation):
    return root/'preservations'/hashlib.sha256(_operation(operation).encode()).hexdigest()


def preservation_holds(configuration, *, guard):
    """Pending intent holds too; unknown, partial or malformed records fail closed."""
    root = _path(str(configuration.root))
    directory = root/'.repository-control'/'preservation-holds'
    guard()
    if not os.path.lexists(directory):
        return set()
    _directory(directory)
    names = sorted(directory.iterdir())
    require(len(names) <= 10000, 'PRESERVATION_HOLD_LIMIT')
    intents, finals, paths = {}, {}, set()
    try:
        for path in names:
            guard()
            require(path.name.endswith('.json'), 'PRESERVATION_HOLD_NAME_INVALID')
            require(not path.is_symlink() and path.is_file(), 'PRESERVATION_HOLD_FILE_INVALID')
            reference = actual_pin(path, guard)
            value = _json(reference)
            if value.get('schemaVersion') == 'MainTargetPreservationHoldIntent/v1':
                exact(value, HOLD_INTENT, 'MainTargetPreservationHoldIntent/v1')
                operation = _operation(value['operationId'])
                archive = _location(root, operation)
                require(path.name == operation+'-intent.json' and value['role'] == ROLE and
                    value['repositoryId'] == configuration.value['repositoryId'] and
                    value['archivePath'] == str(archive) and
                    value['pointPath'] == str(archive/'.repository'/'preservation-point.json') and
                    operation not in intents, 'PRESERVATION_HOLD_SCOPE_INVALID')
                _json(value['preservationIntentPin'])
                intents[operation] = (reference, value)
                paths.add(value['pointPath'])
            else:
                exact(value, HOLD, 'MainTargetPreservationHold/v1')
                operation = _operation(value['operationId'])
                require(path.name == operation+'.json' and value['role'] == ROLE and
                    value['repositoryId'] == configuration.value['repositoryId'] and
                    operation not in finals, 'PRESERVATION_HOLD_SCOPE_INVALID')
                finals[operation] = value
        for operation, value in finals.items():
            require(operation in intents, 'PRESERVATION_HOLD_INTENT_REQUIRED')
            reference, intent = intents[operation]
            require(value['intentPin'] == reference and
                value['targetConfigRef'] == intent['targetConfigRef'] and
                value['pointPin']['path'] == intent['pointPath'], 'PRESERVATION_HOLD_BINDING_CHANGED')
            point, proof = _json(value['pointPin']), _json(value['archiveProofPin'])
            require(point['schemaVersion'] == 'MainTargetPreservationPoint/v1' and
                proof['schemaVersion'] == 'MainTargetPreservationArchive/v1' and
                proof['state'] == 'ARCHIVED_VERIFIED' and proof['operationId'] == operation and
                proof['holdIntentPin'] == reference and proof['pointPin'] == value['pointPin'],
                'PRESERVATION_HOLD_PROOF_CHANGED')
        guard()
        require(sorted(directory.iterdir()) == names, 'PRESERVATION_HOLD_SET_CHANGED')
        return paths
    except (ValueError, KeyError, TypeError, OSError, RepositoryError) as error:
        if isinstance(error, RepositoryError) and error.code.startswith('PRESERVATION_'):
            raise
        raise RepositoryError('PRESERVATION_HOLD_INVALID') from error


class _Deadline:
    def __init__(self, publication):
        self.publication = publication
        self.end = min(publication.session.budget.deadline,
            time.monotonic()+publication.policy['maxPreservationSeconds'])

    def check(self):
        self.publication.check()

    def remaining(self):
        self.check()
        return max(.001, self.end-time.monotonic())


class VerifiedPreservationArchive:
    """Internal evidence value; deliberately has no stage/handoff authority."""
    def __init__(self, publication, reference):
        self._publication = publication
        self.archive_pin = deepcopy(reference)


class _HandoffArchive(VerifiedPreservationArchive):
    """Single publication-owned capability, never a caller supplied pin."""


class VerifiedTargetPreservation:
    def __init__(self, publication, reference):
        self._publication=publication
        self.reference=deepcopy(reference)


class TargetPreservation:
    @classmethod
    def prepare(cls, native, *, policy_pin, reservation_pin):
        view = getattr(native, 'native_context', None)
        require(type(view) is _NativeView and view.phase == 'PREPARATION',
            'PRESERVATION_PREPARATION_REQUIRED')
        view.guard_native(native)
        context = view._context
        target = context._request['targetConfigRef']
        require(context._owner.get('targetPreservationPolicies', {}).get(target) == policy_pin,
            'PRESERVATION_POLICY_UNREGISTERED')
        policy = _json(policy_pin)
        version_two=policy.get('schemaVersion')=='MainTargetPreservationPolicy/v2'
        exact(policy, POLICY, 'MainTargetPreservationPolicy/v2' if version_two else 'MainTargetPreservationPolicy/v1')
        program = context._policy
        require(policy['targetConfigRef'] == target and
            program['captureConfigurationPins'].get(policy['captureRef']) == policy['captureConfigurationPin'] and
            policy['backupEpochPolicy'] == program['backupEpochPolicy'], 'PRESERVATION_POLICY_SCOPE_CHANGED')
        require(all(type(policy[k]) is int and policy[k] > 0 for k in
            ('maxArchiveBytes','maxReadbackRecordBytes','maxPreservationSeconds','minimumFreeBytes')),
            'PRESERVATION_BUDGET_INVALID')
        repository = _json(policy['repositoryConfigurationPin'])
        exact(repository, REPOSITORY_V2 if version_two else REPOSITORY,
            'MainTargetPreservationRepository/v2' if version_two else 'MainTargetPreservationRepository/v1')
        require(type(repository['repositoryId']) is str and repository['repositoryId'],
            'PRESERVATION_REPOSITORY_INVALID')
        root = _path(repository['repositoryRoot']); _directory(root)
        from recovery_replacement_storage import overlaps
        forbidden = [str(context._root), *native.config['dataPaths'], native.config['dataRoot'],
            native.config['replacement']['stateRoot'], program['backupEpochPolicy']['root']]
        require(all(not overlaps(str(root), p) for p in forbidden), 'PRESERVATION_REPOSITORY_OVERLAP')
        if version_two:
            _,_,_,readback=_v2_inputs(native,policy_pin)
        else:readback = _json(repository['readbackConfigPin'])
        require(readback['repositoryRoot'] == str(root) and
            readback['recordRoot'] == str(context._root/'target-preservation'/'publication') and
            readback['maximumTotalRecordBytes'] <= policy['maxReadbackRecordBytes'],
            'PRESERVATION_READBACK_SCOPE_CHANGED')
        # No callback substitutes for the pinned, installed formal binder.
        import formal_capture_recovery_inputs as binder
        require(repository['captureBinderPin']['path'] == str(Path(binder.__file__).resolve()),
            'PRESERVATION_BINDER_CHANGED')
        _read(repository['captureBinderPin'])
        require(getattr(context, '_target_preservation', None) is None, 'PRESERVATION_ALREADY_USED')
        from repository_retention import RepositoryLock
        write_view=None;owner=None;derived=None;view_pin=None
        def preparation_guard():
            view.guard_native(native); context.budget.remaining()
            if write_view is not None:write_view.check()
        configuration = SimpleNamespace(root=root, archives=root/'preservations', value=repository,
            identity_pin=repository['sourceIdentityPin'], current=preparation_guard)
        # The target's real lock is already proved above. This is the existing
        # shared repository byte lock, not a second target lock implementation.
        result = None
        try:
            if version_two:
                # The kernel view is proved before the first repository write.
                write_view=_WriteViewLease(repository)
                from recovery_program_protection import _preservation_root
                parent=_preservation_root(context)
                view_pin=_new(parent/'write-view.json',dict(
                    schemaVersion='MainTargetPreservationWriteViewObservation/v1',
                    operationId=context._request['operationId'],targetConfigRef=target,
                    repositoryConfigurationPin=policy['repositoryConfigurationPin'],
                    executionBindingPin=context._binding,**write_view.observation,observedAt=utc()))
                native.original_pins.append(deepcopy(view_pin))
                derived=_derive_readback_configuration(native,policy_pin=policy_pin)
            preparation_guard()
            owner = RepositoryLock(configuration, context._request)
            preparation_guard()
            with _preparation_view_guard(context,write_view):
                from recovery_target_capture import MainTargetCapture
                session = MainTargetCapture.prepare(native, capture_ref=policy['captureRef'], reservation_pin=reservation_pin)
                source_scope = _json(_json(session.source['objectSourcePin'])['sourceScopePin'])
                preparation_guard()
            require(source_scope['sourceIdentityPin'] == repository['sourceIdentityPin'],
                'PRESERVATION_SOURCE_IDENTITY_CHANGED')
            result = cls.__new__(cls)
            result._closed = result._used = False
            result._pins, result._leases, result._directories = {}, [], {}
            result._repository_lock = owner
            result._write_view=write_view
            result.native, result.context, result.session = native, context, session
            result.policy, result.readback = deepcopy(policy), deepcopy(readback)
            result.policy_pin, result.repository_pin = deepcopy(policy_pin), deepcopy(policy['repositoryConfigurationPin'])
            result.root = context._root/'target-preservation'/'publication'
            if not version_two:result.root.mkdir(mode=0o700)
            result.configuration, result._repository_lock = configuration, owner
            configuration.current = result._check_base
            result.deadline = _Deadline(result)
            result._proof = None
            result._restoration_custody = None
            context._target_preservation = result
            for path in (root, result.root, owner.control): result._directories[path] = _directory(path)
            readback_pins=(repository['readbackTemplatePin'],derived['configurationPin'],
                derived['derivationPin'],view_pin) if version_two else (repository['readbackConfigPin'],)
            for reference in (policy_pin, result.repository_pin, repository['sourceIdentityPin'],
                    *readback_pins, repository['captureBinderPin']):
                result._remember(reference)
            from repository_native_readback import PreservationReadback
            with PreservationReadback(readback, result.deadline) as reader:
                reader.check()
            for reference in (readback['credentialPin'], *readback['libraryPins']): result._remember(reference)
            result._admit_archive_resources()
            execution = _json(context._binding)
            snapshot = _json(execution['contextPin'])
            operation = context._request['operationId']
            result.archive = _location(root, operation)
            intent=dict(
                schemaVersion='MainTargetPreservationIntent/v2' if version_two else 'MainTargetPreservationIntent/v1',
                operationId=operation, targetConfigRef=target,
                role=ROLE, policyPin=policy_pin, repositoryConfigurationPin=result.repository_pin,
                configurationPin=execution['configurationPin'], requestPin=execution['requestPin'],
                originalTargetPin=view.evidence['targetPin'], captureConfigurationPin=session._capture_pin,
                executionBindingPin=context._binding, reservationPin=reservation_pin, contextPin=execution['contextPin'],
                readyEventPin=snapshot['readyEpoch']['eventPin'], replacingEventPin=context._epoch['eventPin'],
                archivePath=str(result.archive), deadlineMonotonic=result.deadline.end, createdAt=utc())
            if version_two:intent.update(readbackDerivationPin=derived['derivationPin'],writeViewObservationPin=view_pin)
            result.intent_pin = result._write(result.root/'intent.json',intent)
            result._hold_before_capture()
            return result
        except BaseException as error:
            try:
                if result is None:
                    try:
                        if owner is not None:owner.close()
                    finally:
                        if write_view is not None:write_view.close()
                else: result.close()
            except BaseException as cleanup:
                error.cleanupError = cleanup
                error.unknown = True
            raise

    def _admit_archive_resources(self):
        from recovery_resource_admission import observe_resources
        budget = self.native.config['resourceBudget']
        observed = observe_resources(self.context._owner,self.context._request,budget)
        devices = {}
        def add(path, amount, free=None):
            self.check()
            info = Path(path).stat(); available = shutil.disk_usage(path).free
            if free is not None: available = min(available,free)
            row = devices.setdefault(info.st_dev,dict(device=info.st_dev,requiredBytes=0,freeBytes=available))
            row['requiredBytes'] += amount; row['freeBytes'] = min(row['freeBytes'],available)
        add(self.configuration.root,self.policy['maxArchiveBytes'])
        add(self.root,self.policy['maxReadbackRecordBytes'])
        add(self.session.root,self.session.budget.maximum+self.session.budget.reserve)
        for row in observed['disks']:
            add(row['path'],budget['diskBytesByPath'][row['path']],row['freeBytes'])
        for row in devices.values():
            row['requiredBytes'] += self.policy['minimumFreeBytes']
            require(row['freeBytes'] >= row['requiredBytes'],'PRESERVATION_ARCHIVE_CAPACITY_INSUFFICIENT')
        self._write(self.root/'resource-admission.json',dict(schemaVersion='MainTargetPreservationResourceAdmission/v1',
            operationId=self.context._request['operationId'],devices=list(devices.values()),admitted=True,observedAt=utc()))

    def _hold_before_capture(self):
        self.check()
        for path in (self.configuration.archives,
                self.configuration.root/'.repository-control'/'preservation-holds'):
            if not os.path.lexists(path): path.mkdir(mode=0o700)
            self._directories[path] = _directory(path)
        preservation_holds(self.configuration,guard=self.check)
        operation = self.context._request['operationId']
        self.hold_intent = self._write(self.configuration.root/'.repository-control'/'preservation-holds'/
            (operation+'-intent.json'),dict(schemaVersion='MainTargetPreservationHoldIntent/v1',
                repositoryId=self.configuration.value['repositoryId'],operationId=operation,
                targetConfigRef=self.context._request['targetConfigRef'],role=ROLE,archivePath=str(self.archive),
                pointPath=str(self.archive/'.repository'/'preservation-point.json'),
                preservationIntentPin=self.intent_pin,createdAt=utc()))

    def _remember(self, reference):
        validate_pin(reference)
        path = reference['path']
        if path in self._pins:
            require(self._pins[path] == reference, 'PRESERVATION_PIN_CONFLICT')
            return reference
        require(actual_pin(path) == reference, 'PRESERVATION_INPUT_CHANGED')
        lease = ArchivePathGuard.capture([path])
        require(actual_pin(path) == reference, 'PRESERVATION_INPUT_CHANGED')
        self._leases.append(lease); self._pins[path] = deepcopy(reference)
        return reference

    def _write(self, path, value):
        self.check()
        reference = _new(path, value)
        self._remember(reference)
        self.native.original_pins.append(deepcopy(reference))
        return reference

    def _check_resources(self):
        """Nonrecursive local custody check used by every context guard."""
        require(not self._closed,'PRESERVATION_CLOSED')
        require(self.context._target_preservation is self and self.session._context is self.context,
            'PRESERVATION_OWNER_CHANGED')
        custody = self._restoration_custody
        if custody is None:
            require(time.monotonic()<self.deadline.end,'PRESERVATION_DEADLINE')
        else:
            # Publication has finished. The enclosing native context still
            # enforces its original owner budget before and after this guard.
            require(type(custody) is VerifiedTargetPreservation and custody is self._final and
                custody._publication is self and self.session.handed_off and self.session._lease.handed_off,
                'PRESERVATION_CUSTODY_CHANGED')
        if self._write_view is not None:self._write_view.check()
        for path,expected in self._directories.items():
            require(_directory(path)==expected,'PRESERVATION_DIRECTORY_CHANGED')
        for lease in self._leases:lease.check()
        # These existing ownership/read-guard checks do not call config.current.
        # Calling RepositoryLock.check here would recurse through ctx._check.
        self._repository_lock._check_owned()
        self._repository_lock._refuse_recovery_read_guard()
        require(not os.path.lexists(self._repository_lock.unknown_path),
            'REPOSITORY_PREVIOUS_WRITE_TERMINAL_UNKNOWN')

    def _check_base(self):
        require(not self._closed, 'PRESERVATION_CLOSED')
        require(self.context._target_preservation is self and self.session._context is self.context,
            'PRESERVATION_OWNER_CHANGED')
        if self.session._state in ('HANDOFF_IN_PROGRESS','HANDED_OFF'):
            # Only local checks after handoff: the original PREPARATION native
            # must not dispatch after generation publication or RESTORE stage.
            self.context._check();self.session.check()
            self.session._lease.check()
        else:self.session.guard()
        self._check_resources()

    def check(self):
        # RepositoryLock.check calls configuration.current (_check_base) once.
        self._repository_lock.check()
        require(not os.path.lexists(self._repository_lock.unknown_path),
            'REPOSITORY_PREVIOUS_WRITE_TERMINAL_UNKNOWN')

    def capture_and_publish(self):
        require(not self._used, 'PRESERVATION_ALREADY_USED')
        self._used = True
        try:
            self.check()
            materials = self.session.capture()
            from repository_minimal import publish_materials
            return publish_materials(self.configuration, materials, publication=self, deadline=self.deadline)
        except BaseException as error:
            if not (self.root/'failure.json').exists():
                snapshot = self.context.snapshot()
                reference = _new(self.root/'failure.json', dict(
                    schemaVersion='MainTargetPreservationFailure/v1', operationId=self.context._request['operationId'],
                    targetConfigRef=self.context._request['targetConfigRef'], phase=self.session.phase,
                    failureCode=getattr(error,'code',type(error).__name__),
                    mutationDispatched=snapshot['mutationDispatched'],
                    terminalUnknown=bool(getattr(error,'unknown',False) or
                        getattr(error,'clientCleanupUncertain',False) or
                        self.session.snapshot()['terminalUnknown'] or snapshot['terminalUnknown']),
                    originalResultPins=deepcopy(list(self._pins.values())), finishedAt=utc()))
                self.native.original_pins.append(reference)
            raise

    def _publish(self, materials):
        from repository_minimal import CapturedPublisher, capture_tree
        from repository_native_readback import PreservationReadback
        from repository_binding import assemble_readback_bindings, repository_binding
        import formal_capture_recovery_inputs as binder
        data = materials.result; root = self.session.root
        inputs = _json(data['captureInputsPin'], 64*1024*1024)
        tree = capture_tree(root, data['captureInputsPin'], inputs)
        require(_json(data['archiveEntriesPin'],64*1024*1024) == tree and
            inputs['pointType'] == 'FULL' and _json(inputs['capturePointPin'])['sourceRestored'] is False,
            'PRESERVATION_MATERIALS_CHANGED')
        total = sum(int(v.split('|')[1]) for v in tree.values() if v != 'directory')
        require(total <= self.policy['maxArchiveBytes'], 'PRESERVATION_ARCHIVE_BUDGET_EXCEEDED')
        from recovery_resource_admission import observe_resources
        budget = self.native.config['resourceBudget']
        observed = observe_resources(self.context._owner,self.context._request,budget)
        device = self.configuration.root.stat().st_dev
        required = total+self.policy['minimumFreeBytes']
        required += sum(budget['diskBytesByPath'][r['path']] for r in observed['disks'] if r['device']==device)
        if self.session.root.stat().st_dev == device:
            required += self.session.budget.maximum+self.session.budget.reserve
        require(shutil.disk_usage(self.configuration.root).free >= required,
            'PRESERVATION_ARCHIVE_CAPACITY_INSUFFICIENT')
        source_files = [root/name for name, spec in tree.items() if spec != 'directory']
        source_dirs = [root, *(root/name for name,spec in tree.items() if spec == 'directory')]
        self._leases.append(ArchivePathGuard.capture(source_files, closed_directories=source_dirs))
        for name, reference in inputs['archiveFilePins'].items():
            require(actual_pin(root/name,self.check) == reference, 'PRESERVATION_MATERIALS_CHANGED')
        require(actual_pin(data['captureInputsPin']['path'],self.check) == data['captureInputsPin'],
            'PRESERVATION_MATERIALS_CHANGED')
        preservation_holds(self.configuration,guard=self.check)
        operation = self.context._request['operationId']; target = self.context._request['targetConfigRef']
        hold_root = self.configuration.root/'.repository-control'/'preservation-holds'
        publisher = CapturedPublisher(self.configuration,root,tree,self.context._request,self.deadline)
        published = publisher.stream(self.archive,tree,verify_content=True)
        close = publisher.archive_request('close')
        require(close['state']=='ARCHIVE_READER_CLOSED_NOT_NAS_PROOF','PRESERVATION_ARCHIVE_CLOSE_FAILED')
        sidecar=self.archive/'.repository';sidecar.mkdir(mode=0o700)
        # Hold the copied payload identities and closed directory membership
        # through full readback, proof validation and eventual typed handoff.
        # The dedicated sidecar exists before closing the archive root; its own
        # membership closes only after all formal sidecars have been written.
        self._leases.append(ArchivePathGuard.capture(
            [self.archive/name for name,spec in tree.items() if spec!='directory'],
            closed_directories=[self.archive,*(self.archive/name for name,spec in tree.items() if spec=='directory')]))
        tree_pin=self._write(sidecar/'payload-tree.json',tree)
        payloads=[published[n] for n in sorted(tree) if tree[n]!='directory']
        manifest=dict(schemaVersion='RepositoryManifest/v1',backupId=inputs['backupId'],generationId=inputs['generationId'],
            pointType='FULL',parentPointPins=[],commonRecoveryPoint=inputs['recoveryPoint'],
            sourceIdentityPin=self.configuration.identity_pin,createdAt=utc(),
            versionPins=inputs['semanticSupplement']['versionPins'],
            toolPins=[actual_pin(p,self.check) for p in self.session.config['tools'].values()],
            payloadRefs=payloads,payloadTreePin=tree_pin,copyProtectionPin=None)
        manifest_pin=self._write(sidecar/'manifest.json',manifest)
        material=dict(manifestPin=manifest_pin,payloadTreePin=tree_pin,payloadRefs=payloads)
        with PreservationReadback(self.readback,self.deadline) as reader:
            connection,originals=reader.verify(str(self.archive),tree,material,payload_content=True)
            self._remember(originals)
            # The retained record closure is checked strictly before invoking
            # the existing binder, whose LIGHT helpers alone are insufficient.
            records=_json(originals,96*1024*1024)
            for reference in records['readbackOriginalPins'].values():self._remember(reference)
            outputs=assemble_readback_bindings(manifest_pin,{'originalRecordsPin':originals},self.deadline,
                binder.assemble_repository_capture_records,verify_content=True)
            recovery=self._write(sidecar/'recovery-material.json',outputs['recoveryMaterial'])
            index=self._write(sidecar/'object-content-index.json',outputs['objectContentIndex'])
            readback=self._write(sidecar/'readback-original.json',dict(schemaVersion='RepositoryMinimumReadback/v1',
                operationId=operation,manifestPin=manifest_pin,independentConnectionId=connection,
                payloadRefs=payloads,originalRecordsPin=originals,payloadContentVerified=True,
                serverDurabilityVerified=False,recoveryMaterialPin=recovery,objectContentIndexPin=index,
                sourceScopePin=outputs['recoveryMaterial']['sourceScopePin']))
            close_pin=self._write(sidecar/'archive-close.json',dict(schemaVersion='RepositoryMinimumArchiveClose/v1',
                operationId=operation,archiveReaderClosed=True,closeResponse=close))
            self.session.guard(force=True)
            snapshot=self.context.snapshot()
            require(not snapshot['terminalUnknown'] and all(row['terminalPin'] is not None and
                row['terminalObservation']['state']=='SUCCEEDED' for row in snapshot['invocations']),
                'PRESERVATION_CAPTURE_TERMINAL_UNPROVEN')
            native_pin=self._write(self.root/'capture-native-evidence.json',snapshot)
            materials_pin=self.session._pins[str(self.session._journal/'materials.json')]
            terminal=self._write(sidecar/'capture-terminal.json',dict(schemaVersion='MainTargetCaptureTerminal/v1',
                operationId=operation,targetConfigRef=target,materialsPin=materials_pin,nativeEvidencePin=native_pin,
                sourceRestored=False,writersRemainQuiesced=True,finishedAt=utc()))
            point={k:manifest[k] for k in ('backupId','generationId','pointType','parentPointPins','commonRecoveryPoint','payloadRefs')}
            point.update(schemaVersion='MainTargetPreservationPoint/v1',role=ROLE,manifestPin=manifest_pin,
                readbackEvidencePin=readback,archiveCloseEvidencePin=close_pin,captureTerminalEvidencePin=terminal,
                integrityState='COMPLETE',controlledRestoreEligible=False)
            point_pin=self._write(sidecar/'preservation-point.json',point)
            binding=self._write(sidecar/'recovery-repository-binding.json',repository_binding(
                SimpleNamespace(policy={'sourceIdentityPin':self.configuration.identity_pin}),
                point_pin,point,recovery,index,verify_metadata=True))
            sidecars=[tree_pin,manifest_pin,recovery,index,readback,close_pin,terminal,point_pin,binding]
            self._leases.append(ArchivePathGuard.capture([p['path'] for p in sidecars],closed_directories=[sidecar]))
            verified=[]
            for reference in sidecars:
                actual,_=reader.read(reference['path'],reference)
                verified.append(actual)
            sidecar_readback=self._write(self.root/'sidecar-readback.json',dict(
                schemaVersion='MainTargetPreservationSidecarReadback/v1',operationId=operation,
                pointPin=point_pin,independentConnectionId=connection,verifiedPins=verified,
                payloadContentVerified=True,serverDurabilityVerified=False,finishedAt=utc()))
        self.session.guard(force=True)
        for reference in list(self._pins.values()):
            require(actual_pin(reference['path'],self.check)==reference,'PRESERVATION_INPUT_CHANGED')
        proof=self._write(self.root/'archive-proof.json',dict(schemaVersion='MainTargetPreservationArchive/v1',
            state='ARCHIVED_VERIFIED',operationId=operation,targetConfigRef=target,role=ROLE,
            intentPin=self.intent_pin,materialsPin=materials_pin,holdIntentPin=self.hold_intent,pointPin=point_pin,
            manifestPin=manifest_pin,payloadTreePin=tree_pin,repositoryBindingPin=binding,recoveryMaterialPin=recovery,
            objectContentIndexPin=index,readbackPin=readback,sidecarReadbackPin=sidecar_readback,
            archiveClosePin=close_pin,captureTerminalPin=terminal,payloadContentVerified=True,
            serverDurabilityVerified=False,independentFailureDomain=False,
            originalResultPins=deepcopy(list(self._pins.values())),finishedAt=utc()))
        self._write(hold_root/(operation+'.json'),dict(schemaVersion='MainTargetPreservationHold/v1',
            repositoryId=self.configuration.value['repositoryId'],operationId=operation,targetConfigRef=target,
            role=ROLE,intentPin=self.hold_intent,pointPin=point_pin,archiveProofPin=proof,createdAt=utc()))
        self._proof=proof
        validate_archive(self.native,proof)
        return proof

    def handoff(self):
        require(getattr(self,'_handoff_archive',None) is None,'PRESERVATION_HANDOFF_ALREADY_USED')
        require(self._proof is not None,'PRESERVATION_ARCHIVE_REQUIRED')
        self.check()
        # Initial publication already performed full strict readback and
        # validate_archive. Continuous leases have remained held since then.
        proof=_json(self._proof)
        exact(proof,PROOF,'MainTargetPreservationArchive/v1')
        require(proof['intentPin']==self.intent_pin and proof['state']=='ARCHIVED_VERIFIED',
            'PRESERVATION_PROOF_INVALID')
        self._handoff_archive=_HandoffArchive(self,self._proof)
        handoff=self.session.handoff(self._handoff_archive)
        hold=self._pins[str(self.configuration.root/'.repository-control'/'preservation-holds'/
            (self.context._request['operationId']+'.json'))]
        reference=self._write(self.root/'preservation.json',dict(schemaVersion='MainTargetPreservation/v1',
            state='SUCCEEDED',operationId=self.context._request['operationId'],
            targetConfigRef=self.context._request['targetConfigRef'],policyPin=self.policy_pin,
            intentPin=self.intent_pin,archiveProofPin=self._proof,handoffPin=handoff,holdPin=hold,
            originalResultPins=deepcopy(list(self._pins.values())),finishedAt=utc()))
        self._final=VerifiedTargetPreservation(self,reference)
        require_preservation(self.context,native=self.native)
        # Seal only after the complete final proof passes under the original
        # publication deadline; HANDED_OFF alone never transfers the clock.
        self._restoration_custody=self._final
        return self._final

    def close(self):
        if self._closed:return
        self._closed=True
        try:
            for lease in reversed(self._leases):lease.close()
        finally:
            self._leases=[]
            try:self._repository_lock.close()
            finally:
                if self._write_view is not None:self._write_view.close()


def validate_archive(native, archive_proof_pin):
    view=getattr(native,'native_context',None)
    require(type(view) is _NativeView,'PRESERVATION_CONTEXT_REQUIRED')
    publication=getattr(view._context,'_target_preservation',None)
    require(type(publication) is TargetPreservation and publication.native is native and
        publication._proof==archive_proof_pin,'PRESERVATION_PROOF_OWNER_CHANGED')
    publication.check()
    proof=_json(archive_proof_pin)
    exact(proof,PROOF,'MainTargetPreservationArchive/v1')
    require(proof['state']=='ARCHIVED_VERIFIED' and proof['role']==ROLE and
        proof['payloadContentVerified'] is True and proof['serverDurabilityVerified'] is False and
        proof['independentFailureDomain'] is False and proof['intentPin']==publication.intent_pin and
        proof['operationId']==publication.context._request['operationId'] and
        proof['targetConfigRef']==publication.context._request['targetConfigRef'], 'PRESERVATION_PROOF_INVALID')
    point=_json(proof['pointPin']);exact(point,POINT,'MainTargetPreservationPoint/v1')
    require(point['role']==ROLE and point['pointType']=='FULL' and point['parentPointPins']==[] and
        point['integrityState']=='COMPLETE' and point['controlledRestoreEligible'] is False,
        'PRESERVATION_POINT_INVALID')
    for reference in proof['originalResultPins']:
        require(actual_pin(reference['path'],publication.check)==reference,'PRESERVATION_INPUT_CHANGED')
    for reference in point['payloadRefs']:
        require(actual_pin(reference['path'],publication.check)==reference,'PRESERVATION_PAYLOAD_CHANGED')
    require(proof['pointPin']['path'] in preservation_holds(publication.configuration,guard=publication.check),
        'PRESERVATION_HOLD_REQUIRED')
    publication.check()
    return VerifiedPreservationArchive(publication,archive_proof_pin)


def require_preservation(context, *, native=None):
    """Live authorization requires the exact operation-owned final object.

    This performs bounded metadata and continuous identity checks, never a
    second full read of payloads already held since strict publication.
    """
    from recovery_program_native import MainNativeExecutionContext
    from recovery_engine import require as execution_require
    execution_require(type(context) is MainNativeExecutionContext,'PRESERVATION_CONTEXT_REQUIRED')
    context._check()
    policies=context._owner.get('targetPreservationPolicies',{})
    target=context._request['targetConfigRef']
    if target not in policies:return None
    publication=getattr(context,'_target_preservation',None)
    execution_require(type(publication) is TargetPreservation and
        publication.context is context and publication.policy_pin==policies[target],
        'PROGRAM_TARGET_PRESERVATION_REQUIRED')
    final=getattr(publication,'_final',None)
    execution_require(type(final) is VerifiedTargetPreservation and final._publication is publication and
        publication.session.handed_off and publication.session._lease.handed_off,
        'PROGRAM_TARGET_PRESERVATION_REQUIRED')
    publication.check()
    execution_require(final.reference is not None and
        final.reference==publication._pins.get(str(publication.root/'preservation.json')),
        'PRESERVATION_FINAL_CHANGED')
    value=_json(final.reference)
    exact(value,'schemaVersion state operationId targetConfigRef policyPin intentPin archiveProofPin '
        'handoffPin holdPin originalResultPins finishedAt','MainTargetPreservation/v1')
    execution_require(value['state']=='SUCCEEDED' and value['operationId']==context._request['operationId'] and
        value['targetConfigRef']==target and value['policyPin']==policies[target] and
        value['intentPin']==publication.intent_pin and value['archiveProofPin']==publication._proof,
        'PRESERVATION_FINAL_CHANGED')
    intent=_json(value['intentPin']);handoff=_json(value['handoffPin'])
    execution_require(intent['configurationPin']==_json(context._binding)['configurationPin'] and
        intent['executionBindingPin']==context._binding and
        handoff['schemaVersion']=='MainTargetPreservationHandoff/v1' and handoff['state']=='SUCCEEDED' and
        handoff['operationId']==value['operationId'] and handoff['targetConfigRef']==target and
        handoff['archiveProofPin']==publication._proof and
        _json(handoff['intentPin'])['bindingPin']==context._binding,
        'PRESERVATION_FINAL_CHANGED')
    hold=_json(value['holdPin'])
    execution_require(hold['pointPin']==_json(publication._proof)['pointPin'] and
        hold['archiveProofPin']==publication._proof,'PRESERVATION_HOLD_REQUIRED')
    if native is not None:
        view=getattr(native,'native_context',None)
        execution_require(type(view) is _NativeView and view._context is context and
            native.protection_custody is publication.session._custody,'PRESERVATION_OWNER_CHANGED')
        view.guard_native(native)
        publication.session._custody._validate(native)
    publication.check()
    return final


def validate_preservation_evidence(owner,request,reference,*,binding_pin,guard=None,_reader=None):
    """Verify retained archive facts offline; never construct a live clear grant.

    The existing strict readback binder verifies the actual archived payloads.
    Operation-local metadata shares the historical reader's bounded reads and
    final identity checks. A caller cannot substitute this report for the live
    same-context object and continuously held leases required above.
    """
    from recovery_engine import canonical as native_canonical,digest
    from recovery_program_evidence import _Reader
    from recovery_program_execution import BINDING_FIELDS
    from recovery_program_activation import CONTEXT_FIELDS
    from repository_binding import assemble_readback_bindings,repository_binding
    import formal_capture_recovery_inputs as binder
    guard=(lambda:None) if guard is None else guard
    try:
        require(callable(guard),'PRESERVATION_EVIDENCE_INVALID')
        operation=request['operationId'];target=request['targetConfigRef']
        root=_path(owner['operationsRoot'])/_operation(operation)
        claim=_path(owner['targets'][target]['replacement']['stateRoot'])/operation
        publication=root/'target-preservation'/'publication'
        reader=_Reader(guard,(root,claim)) if _reader is None else _reader
        require(type(reader) is _Reader and reader.roots==(root,claim),'PRESERVATION_EVIDENCE_INVALID')
        def read(pin,maximum=4*1024*1024):return reader.read(pin,maximum)
        def fixed(pin,path,maximum=4*1024*1024):
            require(_path(pin['path'])==path,'PRESERVATION_EVIDENCE_PATH_CHANGED')
            return read(pin,maximum)
        value=fixed(reference,publication/'preservation.json')
        exact(value,'schemaVersion state operationId targetConfigRef policyPin intentPin archiveProofPin '
            'handoffPin holdPin originalResultPins finishedAt','MainTargetPreservation/v1')
        require(value['state']=='SUCCEEDED' and value['operationId']==operation and
            value['targetConfigRef']==target and owner['targetPreservationPolicies'][target]==value['policyPin'],
            'PRESERVATION_EVIDENCE_SCOPE_CHANGED')
        policy=read(value['policyPin'])
        version_two=policy.get('schemaVersion')=='MainTargetPreservationPolicy/v2'
        exact(policy,POLICY,'MainTargetPreservationPolicy/v2' if version_two else 'MainTargetPreservationPolicy/v1')
        program=owner['targetProgramPolicies'][target]
        require(policy['targetConfigRef']==target and policy['backupEpochPolicy']==program['backupEpochPolicy'] and
            program['captureConfigurationPins'][policy['captureRef']]==policy['captureConfigurationPin'],
            'PRESERVATION_EVIDENCE_POLICY_CHANGED')
        repository=read(policy['repositoryConfigurationPin'])
        exact(repository,REPOSITORY_V2 if version_two else REPOSITORY,
            'MainTargetPreservationRepository/v2' if version_two else 'MainTargetPreservationRepository/v1')
        archive=_location(_path(repository['repositoryRoot']),operation);sidecar=archive/'.repository'
        binding=fixed(binding_pin,claim/'program-execution-binding.json')
        require(type(binding) is dict and set(binding)==BINDING_FIELDS and
            binding['schemaVersion']=='MainProgramExecutionBinding/v1' and binding['operationId']==operation and
            binding['targetConfigRef']==target and binding['policySha256']==digest(program) and
            fixed(binding['configurationPin'],root/'configuration.json')==owner and
            fixed(binding['requestPin'],root/'request.json')==request,
            'PRESERVATION_EVIDENCE_BINDING_CHANGED')
        context=fixed(binding['contextPin'],claim/'program-context.json')
        require(type(context) is dict and set(context)==CONTEXT_FIELDS and
            context['schemaVersion']=='MainProgramRestoreContext/v1' and context['operationId']==operation and
            context['policySha256']==digest(program),'PRESERVATION_EVIDENCE_CONTEXT_CHANGED')
        intent=fixed(value['intentPin'],publication/'intent.json')
        require(intent.get('schemaVersion')==('MainTargetPreservationIntent/v2' if version_two else 'MainTargetPreservationIntent/v1') and
            intent['operationId']==operation and intent['targetConfigRef']==target and intent['role']==ROLE and
            intent['policyPin']==value['policyPin'] and intent['repositoryConfigurationPin']==policy['repositoryConfigurationPin'] and
            intent['configurationPin']==binding['configurationPin'] and intent['requestPin']==binding['requestPin'] and
            intent['executionBindingPin']==binding_pin and intent['contextPin']==binding['contextPin'] and
            intent['originalTargetPin']==context['targetPin'] and
            intent['captureConfigurationPin']==context['capturePins'][policy['captureRef']] and
            intent['reservationPin']==binding['reservationPin'] and intent['archivePath']==str(archive) and
            intent['readyEventPin']==context['readyEpoch']['eventPin'],
            'PRESERVATION_EVIDENCE_INTENT_CHANGED')
        if version_two:
            exact(intent,'schemaVersion operationId targetConfigRef role policyPin repositoryConfigurationPin '
                'configurationPin requestPin originalTargetPin captureConfigurationPin executionBindingPin '
                'reservationPin contextPin readyEventPin replacingEventPin archivePath deadlineMonotonic '
                'createdAt readbackDerivationPin writeViewObservationPin','MainTargetPreservationIntent/v2')
            capture=read(policy['captureConfigurationPin'])
            from minimal_capture_support import validate_main_target_config
            validate_main_target_config(capture)
            _read_v2_admission(reader,policy_pin=value['policyPin'],policy=policy,repository=repository,
                request=request,root=root,binding_pin=binding_pin,
                derivation_pin=intent['readbackDerivationPin'],view_pin=intent['writeViewObservationPin'])
        proof=fixed(value['archiveProofPin'],publication/'archive-proof.json')
        exact(proof,PROOF,'MainTargetPreservationArchive/v1')
        require(proof['state']=='ARCHIVED_VERIFIED' and proof['role']==ROLE and proof['operationId']==operation and
            proof['targetConfigRef']==target and proof['intentPin']==value['intentPin'] and
            proof['payloadContentVerified'] is True and proof['serverDurabilityVerified'] is False and
            proof['independentFailureDomain'] is False,'PRESERVATION_EVIDENCE_ARCHIVE_CHANGED')
        names=dict(pointPin='preservation-point.json',manifestPin='manifest.json',payloadTreePin='payload-tree.json',
            repositoryBindingPin='recovery-repository-binding.json',recoveryMaterialPin='recovery-material.json',
            objectContentIndexPin='object-content-index.json',readbackPin='readback-original.json',
            archiveClosePin='archive-close.json',captureTerminalPin='capture-terminal.json')
        docs={key:fixed(proof[key],sidecar/name,64*1024*1024 if key in
            ('recoveryMaterialPin','objectContentIndexPin') else 4*1024*1024) for key,name in names.items()}
        require(set(reader.listing(sidecar))==set(names.values()),'PRESERVATION_EVIDENCE_SIDECAR_CHANGED')
        point=docs['pointPin'];exact(point,POINT,'MainTargetPreservationPoint/v1')
        manifest=docs['manifestPin'];tree=docs['payloadTreePin'];readback=docs['readbackPin']
        require(point['role']==ROLE and point['pointType']=='FULL' and point['parentPointPins']==[] and
            point['integrityState']=='COMPLETE' and point['controlledRestoreEligible'] is False and
            all(point[k]==manifest[k] for k in ('backupId','generationId','pointType','parentPointPins',
                'commonRecoveryPoint','payloadRefs')) and point['manifestPin']==proof['manifestPin'] and
            point['readbackEvidencePin']==proof['readbackPin'] and
            point['archiveCloseEvidencePin']==proof['archiveClosePin'] and
            point['captureTerminalEvidencePin']==proof['captureTerminalPin'] and
            manifest['payloadTreePin']==proof['payloadTreePin'] and
            manifest['sourceIdentityPin']==repository['sourceIdentityPin'],
            'PRESERVATION_EVIDENCE_POINT_CHANGED')
        require(type(tree) is dict and tree and type(point['payloadRefs']) is list,
            'PRESERVATION_EVIDENCE_TREE_INVALID')
        expected_files={};directories={archive}
        for name,spec in tree.items():
            guard();path=_path(str(archive/name))
            require(type(name) is str and path!=archive and archive in path.parents and
                '.repository' not in Path(name).parts,'PRESERVATION_EVIDENCE_TREE_INVALID')
            if spec=='directory':directories.add(path)
            else:
                fields=spec.split('|')
                require(len(fields)==3 and fields[0]=='file' and fields[1].isdigit(),
                    'PRESERVATION_EVIDENCE_TREE_INVALID')
                expected_files[str(path)]=dict(path=str(path),bytes=int(fields[1]),sha256=fields[2])
        require(sorted(point['payloadRefs'],key=lambda p:p['path'])==
            sorted(expected_files.values(),key=lambda p:p['path']),'PRESERVATION_EVIDENCE_PAYLOAD_SET_CHANGED')
        for directory in directories:
            children={Path(p).name for p in [*expected_files,*map(str,directories)] if Path(p).parent==directory}
            if directory==archive:children.add('.repository')
            require(set(reader.listing(directory))==children,'PRESERVATION_EVIDENCE_TREE_CHANGED')
        for payload in point['payloadRefs']:reader.payload(payload)
        require(readback.get('schemaVersion')=='RepositoryMinimumReadback/v1' and
            readback['operationId']==operation and readback['manifestPin']==proof['manifestPin'] and
            readback['payloadRefs']==point['payloadRefs'] and readback['payloadContentVerified'] is True and
            readback['serverDurabilityVerified'] is False and
            readback['recoveryMaterialPin']==proof['recoveryMaterialPin'] and
            readback['objectContentIndexPin']==proof['objectContentIndexPin'],
            'PRESERVATION_EVIDENCE_READBACK_CHANGED')
        originals=read(readback['originalRecordsPin'],96*1024*1024)
        exact(originals,'schemaVersion manifestPin archivedFilePins readbackOriginalPins','RepositoryReadbackOriginals/v1')
        require(originals['manifestPin']==proof['manifestPin'] and
            sum(p['bytes'] for p in originals['readbackOriginalPins'].values())<=policy['maxReadbackRecordBytes'],
            'PRESERVATION_EVIDENCE_READBACK_CHANGED')
        for pin in originals['readbackOriginalPins'].values():reader.blob(pin)
        reader.blob(repository['captureBinderPin'])
        require(repository['captureBinderPin']['path']==str(Path(binder.__file__).resolve()),
            'PRESERVATION_EVIDENCE_BINDER_CHANGED')
        outputs=assemble_readback_bindings(proof['manifestPin'],{'originalRecordsPin':readback['originalRecordsPin']},
            SimpleNamespace(check=guard),binder.assemble_repository_capture_records,verify_content=True)
        require(outputs==dict(recoveryMaterial=docs['recoveryMaterialPin'],objectContentIndex=docs['objectContentIndexPin']),
            'PRESERVATION_EVIDENCE_MATERIAL_CHANGED')
        expected_binding=repository_binding(SimpleNamespace(policy={'sourceIdentityPin':repository['sourceIdentityPin']}),
            proof['pointPin'],point,proof['recoveryMaterialPin'],proof['objectContentIndexPin'],verify_metadata=True)
        require(docs['repositoryBindingPin']==expected_binding,'PRESERVATION_EVIDENCE_REPOSITORY_BINDING_CHANGED')
        close=docs['archiveClosePin'];terminal=docs['captureTerminalPin']
        require(close.get('schemaVersion')=='RepositoryMinimumArchiveClose/v1' and close['operationId']==operation and
            close['archiveReaderClosed'] is True and close['closeResponse']['state']=='ARCHIVE_READER_CLOSED_NOT_NAS_PROOF' and
            terminal.get('schemaVersion')=='MainTargetCaptureTerminal/v1' and terminal['operationId']==operation and
            terminal['targetConfigRef']==target and terminal['materialsPin']==proof['materialsPin'] and
            terminal['sourceRestored'] is False and terminal['writersRemainQuiesced'] is True,
            'PRESERVATION_EVIDENCE_CAPTURE_TERMINAL_CHANGED')
        materials=fixed(proof['materialsPin'],root/'target-preservation'/'session'/'materials.json')
        require(materials.get('schemaVersion')=='MainTargetCaptureMaterials/v1' and materials['operationId']==operation and
            materials['writersRemainQuiesced'] is True and materials['sourceRestored'] is False,
            'PRESERVATION_EVIDENCE_MATERIALS_CHANGED')
        native=fixed(terminal['nativeEvidencePin'],publication/'capture-native-evidence.json',64*1024*1024)
        require(native.get('schemaVersion')=='MainNativeExecutionEvidence/v1' and native['operationId']==operation and
            native['bindingPin']==binding_pin and native['generationPin'] is None and native['phase']=='PREPARATION' and
            native['terminalUnknown'] is False,'PRESERVATION_EVIDENCE_NATIVE_CHANGED')
        pins=[]
        for sequence,row in enumerate(native['invocations']):
            intent_row=row['intentObservation'];dispatch=row['intentPinAtDispatch'];terminal_row=read(row['terminalPin'])
            require(row['sequence']==sequence and row['phase']=='PREPARATION' and
                len(native_canonical(intent_row))==dispatch['bytes'] and digest(intent_row)==dispatch['sha256'] and
                intent_row['schemaVersion']=='RecoveryDataInvocation/v1' and intent_row['operationId']==operation and
                intent_row['action']=='RESTORE' and type(intent_row['mutation']) is bool and
                intent_row['actualExitCode'] is None and intent_row['finishedAt'] is None and
                intent_row['state']=='TERMINAL_UNKNOWN' and row['terminalPin']['path']==dispatch['path'] and
                terminal_row==row['terminalObservation'] and terminal_row['state']=='SUCCEEDED' and
                type(terminal_row['actualExitCode']) is int and terminal_row['actualExitCode']==0 and
                all(terminal_row[k]==intent_row[k] for k in
                    ('schemaVersion','operationId','action','argvSha256','mutation','startedAt')),
                'PRESERVATION_EVIDENCE_NATIVE_CHANGED')
            pins.append(row['terminalPin'])
        require(pins==native['originalResultPins'] and native['mutationDispatched'] is
            any(r['intentObservation']['mutation'] for r in native['invocations']) and
            native['lastExitCode']==(0 if pins else None),'PRESERVATION_EVIDENCE_NATIVE_CHANGED')
        side=fixed(proof['sidecarReadbackPin'],publication/'sidecar-readback.json')
        require(side.get('schemaVersion')=='MainTargetPreservationSidecarReadback/v1' and side['operationId']==operation and
            side['pointPin']==proof['pointPin'] and side['independentConnectionId']==readback['independentConnectionId'] and
            side['verifiedPins']==[proof[k] for k in ('payloadTreePin','manifestPin','recoveryMaterialPin',
                'objectContentIndexPin','readbackPin','archiveClosePin','captureTerminalPin','pointPin','repositoryBindingPin')] and
            side['payloadContentVerified'] is True and side['serverDurabilityVerified'] is False,
            'PRESERVATION_EVIDENCE_SIDECAR_CHANGED')
        handoff=fixed(value['handoffPin'],root/'target-preservation'/'session'/'handoff.json')
        handoff_intent=fixed(handoff['intentPin'],root/'target-preservation'/'session'/'handoff-intent.json')
        require(handoff.get('schemaVersion')=='MainTargetPreservationHandoff/v1' and handoff['state']=='SUCCEEDED' and
            handoff['operationId']==operation and handoff['targetConfigRef']==target and
            handoff['archiveProofPin']==value['archiveProofPin'] and
            handoff_intent.get('schemaVersion')=='MainTargetPreservationHandoffIntent/v1' and
            handoff_intent['operationId']==operation and handoff_intent['targetConfigRef']==target and
            handoff_intent['bindingPin']==binding_pin and handoff_intent['archiveProofPin']==value['archiveProofPin'] and
            handoff_intent['originalFlags']==[1,1] and handoff_intent['restoreFlags']==[0,0],
            'PRESERVATION_EVIDENCE_HANDOFF_CHANGED')
        hold_root=_path(repository['repositoryRoot'])/'.repository-control'/'preservation-holds'
        hold=fixed(value['holdPin'],hold_root/(operation+'.json'))
        hold_intent=fixed(hold['intentPin'],hold_root/(operation+'-intent.json'))
        exact(hold,HOLD,'MainTargetPreservationHold/v1')
        exact(hold_intent,HOLD_INTENT,'MainTargetPreservationHoldIntent/v1')
        require(hold['role']==hold_intent['role']==ROLE and
            hold['repositoryId']==hold_intent['repositoryId']==repository['repositoryId'] and
            hold['operationId']==hold_intent['operationId']==operation and
            hold['targetConfigRef']==hold_intent['targetConfigRef']==target and
            hold['pointPin']==proof['pointPin'] and hold['archiveProofPin']==value['archiveProofPin'] and
            hold['intentPin']==proof['holdIntentPin'] and hold_intent['preservationIntentPin']==value['intentPin'] and
            hold_intent['archivePath']==str(archive) and hold_intent['pointPath']==proof['pointPin']['path'],
            'PRESERVATION_EVIDENCE_HOLD_CHANGED')
        for aggregate in (proof,value,handoff):
            for pin in aggregate['originalResultPins']:
                if _path(pin['path']) not in reader.records:reader.blob(pin)
        reader.unchanged()
        return dict(schemaVersion='MainTargetPreservationEvidenceValidation/v1',operationId=operation,
            targetPreservationPin=deepcopy(reference),payloadContentVerified=True,
            captureNativeEvidencePin=deepcopy(terminal['nativeEvidencePin']),captureInvocations=deepcopy(native['invocations']),
            originalResultPins=[deepcopy(row[0]) for row in reader.records.values()],clearAuthorized=False)
    except RepositoryError:raise
    except (RecoveryError,KeyError,TypeError,ValueError,IndexError,AttributeError,OSError) as error:
        raise RepositoryError('PRESERVATION_EVIDENCE_INVALID') from error
